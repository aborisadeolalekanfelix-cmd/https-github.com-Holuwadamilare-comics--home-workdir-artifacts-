#!/usr/bin/env python3
"""
Secure Webhook Receiver with TikTok Auto-Posting
For the Abyss Masterpiece / Kling AI content pipeline

Now handles:
- Signature verification
- TikTok auto-posting when receiving "video_generation_complete" event
- Supports both PULL_FROM_URL and FILE_UPLOAD methods
"""

import os
import sys
import json
import hmac
import hashlib
import time
import requests
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ==================== CONFIG ====================
PORT = int(os.environ.get("WEBHOOK_PORT", 8080))
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").encode()

# TikTok
TIKTOK_ACCESS_TOKEN = os.environ.get("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_API_BASE = "https://open.tiktokapis.com"

if not WEBHOOK_SECRET:
    print("WARNING: WEBHOOK_SECRET not set!")
    WEBHOOK_SECRET = b"CHANGE_THIS_SECRET_IMMEDIATELY"

# ==================== TIKTOK POSTING LOGIC ====================

def generate_tiktok_caption(episode_num: int, title: str) -> str:
    captions = {
        1: f"He was sleeping for centuries… until the Dragon Staff chose him.\n\nEpisode 1 of the Abyss Masterpiece series.\n\nFull playlist in bio 👆\n\n#AbyssMasterpiece #DragonStaffWizard #CinematicFantasy",
        2: f"The ruins have been waiting…\n\nAfter awakening the Dragon Staff, something ancient has begun to stir.\n\nEpisode 2 is live.\n\nFull series in bio 👆\n\n#AbyssMasterpiece #CinematicAbyss",
        3: f"The pact is revealed…\n\nThe wizard learns the true cost of power.\n\nEpisode 3 drops now.\n\nWatch the full cinematic series 👆\n\n#AbyssMasterpiece #DragonStaff",
    }
    return captions.get(episode_num, f"Episode {episode_num}: {title}\n\nFull series in bio 👆\n\n#AbyssMasterpiece #CinematicFantasy")

def post_to_tiktok(video_url: str = None, local_video_path: str = None, 
                   caption: str = "", privacy_level: str = "PUBLIC_TO_EVERYONE",
                   upload_method: str = "pull_from_url") -> bool:
    """Post to TikTok (supports both methods)"""
    if not TIKTOK_ACCESS_TOKEN:
        print("❌ TIKTOK_ACCESS_TOKEN not set in webhook environment.")
        return False

    init_url = f"{TIKTOK_API_BASE}/v2/post/publish/video/init/"

    if upload_method == "pull_from_url":
        if not video_url:
            print("❌ video_url required for pull_from_url")
            return False

        payload = {
            "post_info": {
                "title": caption[:2200],
                "privacy_level": privacy_level,
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url
            }
        }

        headers = {
            "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        try:
            print("📤 Posting to TikTok (PULL_FROM_URL)...")
            r = requests.post(init_url, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
            if data.get("error") is None and data.get("data"):
                print(f"✅ TikTok post initialized! publish_id: {data['data'].get('publish_id')}")
                return True
            print(f"❌ TikTok error: {data}")
            return False
        except Exception as e:
            print(f"❌ TikTok posting failed: {e}")
            return False

    elif upload_method == "file_upload":
        if not local_video_path or not os.path.exists(local_video_path):
            print("❌ local_video_path required for file_upload")
            return False

        file_size = os.path.getsize(local_video_path)
        chunk_size = 5 * 1024 * 1024

        init_payload = {
            "post_info": {
                "title": caption[:2200],
                "privacy_level": privacy_level,
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": chunk_size,
                "total_chunk_count": (file_size + chunk_size - 1) // chunk_size
            }
        }

        headers = {"Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}", "Content-Type": "application/json"}

        try:
            print("📤 Initializing TikTok FILE_UPLOAD...")
            r = requests.post(init_url, json=init_payload, headers=headers, timeout=30)
            r.raise_for_status()
            init_data = r.json()

            if init_data.get("error") or not init_data.get("data"):
                print(f"❌ TikTok init error: {init_data}")
                return False

            upload_url = init_data["data"]["upload_url"]
            publish_id = init_data["data"]["publish_id"]
            print(f"✅ Upload initialized. publish_id: {publish_id}")

            # Chunked upload
            with open(local_video_path, "rb") as f:
                chunk_index = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    start = chunk_index * chunk_size
                    end = start + len(chunk) - 1

                    chunk_headers = {
                        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
                        "Content-Type": "video/mp4",
                        "Content-Range": f"bytes {start}-{end}/{file_size}"
                    }
                    upload_r = requests.put(upload_url, data=chunk, headers=chunk_headers, timeout=60)
                    if upload_r.status_code not in [200, 201, 206]:
                        print(f"❌ Chunk {chunk_index} failed")
                        return False
                    print(f"   Uploaded chunk {chunk_index + 1}")
                    chunk_index += 1

            print("✅ FILE_UPLOAD completed successfully!")
            return True

        except Exception as e:
            print(f"❌ FILE_UPLOAD failed: {e}")
            return False

    return False

# ==================== WEBHOOK HANDLER ====================

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/webhook":
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        signature_header = self.headers.get('X-Hub-Signature-256', '')
        if not signature_header.startswith('sha256='):
            self.send_error(401, "Missing signature")
            return

        provided_signature = signature_header.split('=', 1)[1]
        expected_signature = hmac.new(WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(provided_signature, expected_signature):
            print(f"[{datetime.now()}] ❌ Invalid signature")
            self.send_error(401, "Invalid signature")
            return

        try:
            payload = json.loads(body.decode('utf-8'))
        except:
            payload = {"raw_body": body.decode('utf-8', errors='replace')}

        print(f"\n[{datetime.now()}] ✅ Valid webhook received: {payload.get('event')}")

        # ==================== TIKTOK AUTO-POSTING LOGIC ====================
        event = payload.get("event")
        if event == "video_generation_complete":
            video_url = payload.get("video_url")
            episode = payload.get("episode", 1)
            title = payload.get("title", f"Episode {episode}")

            if video_url and TIKTOK_ACCESS_TOKEN:
                print("🎬 Triggering TikTok auto-posting from webhook...")
                caption = generate_tiktok_caption(episode, title)

                # Default to PULL_FROM_URL (can be changed to "file_upload" if needed)
                success = post_to_tiktok(
                    video_url=video_url,
                    caption=caption,
                    upload_method="pull_from_url"
                )

                if success:
                    print("✅ TikTok posting initiated from webhook handler")
            else:
                print("⚠️  Missing video_url or TIKTOK_ACCESS_TOKEN — skipping TikTok post")

        # Respond
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {
            "status": "success",
            "message": "Webhook processed",
            "event": event,
            "timestamp": datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def log_message(self, format, *args):
        pass

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, WebhookHandler)
    print(f"🚀 Secure Webhook + TikTok Poster running on port {PORT}")
    print(f"   Endpoint: http://localhost:{PORT}/webhook")
    print(f"   TikTok posting: {'ENABLED' if TIKTOK_ACCESS_TOKEN else 'DISABLED (no TIKTOK_ACCESS_TOKEN)'}")
    print("\nPress Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()