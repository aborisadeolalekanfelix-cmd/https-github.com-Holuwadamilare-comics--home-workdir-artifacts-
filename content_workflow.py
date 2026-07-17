#!/usr/bin/env python3
"""
Abyss Masterpiece Content Production Workflow
Complete end-to-end automation for the cinematic TikTok series.

This workflow:
1. Generates consistent keyframes using the character bible
2. Prepares optimized prompts for Kling AI
3. Sends completion event to the secure webhook
4. Handles episode progression and playlist updates

Usage:
    python3 content_workflow.py --episode 3 --title "The Dragon’s Pact"

Requirements:
    pip install requests
"""

import os
import json
import hmac
import hashlib
import requests
import argparse
from datetime import datetime
from pathlib import Path

# ==================== CONFIGURATION ====================
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "http://localhost:8080/webhook")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").encode()

# Character Bible (from the original abyss-cinematic-wizard skill)
CHARACTER_BIBLE = """
Core Character Rules (Strict Consistency):
- Tall imposing male wizard, early 40s, athletic build
- Long flowing silver-white hair moving underwater
- Pale skin with cyan bioluminescent runes on face, neck, hands
- Piercing cyan-blue glowing eyes
- Flowing dark teal and midnight-black abyssal robes with golden sea rune embroidery
- Ornate Dragon Staff: black coral + obsidian, sea dragon head with golden-orange fire
"""

# Episode progression (simple state)
EPISODES = {
    1: {"title": "The Awakening", "focus": "Staff activation + first power surge"},
    2: {"title": "The Call of the Ruins", "focus": "Ruins react, staff shoots light beam"},
    3: {"title": "The Dragon’s Pact", "focus": "Vision of the ancient pact"},
    4: {"title": "Shadows in the Deep", "focus": "First confrontation with corrupted entities"},
}

# ==================== HELPER FUNCTIONS ====================

def generate_keyframe_prompt(episode_num: int, moment: str) -> str:
    """Generate a highly consistent Kling AI / image prompt."""
    episode = EPISODES.get(episode_num, {"title": f"Episode {episode_num}", "focus": "Unknown"})
    
    prompt = f"""Masterpiece cinematic still, Episode {episode_num}: {episode['title']}.
{moment}

{CHARACTER_BIBLE}

Cinematic style: Hyper-detailed dark fantasy realism, teal-orange color grade, 
dramatic volumetric god rays, shallow depth of field, anamorphic bokeh, 
majestic mysterious powerful ancient mood. 9:16 vertical composition.
"""
    return prompt.strip()


def sign_payload(payload: dict) -> str:
    """Create HMAC-SHA256 signature for the webhook."""
    body = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def send_to_webhook(event: str, payload: dict):
    """Send authenticated event to the secure webhook."""
    if not WEBHOOK_SECRET:
        print("⚠️  WEBHOOK_SECRET not set. Skipping webhook call.")
        return

    full_payload = {
        "event": event,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **payload
    }

    signature = sign_payload(full_payload)
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature
    }

    try:
        response = requests.post(
            WEBHOOK_URL,
            json=full_payload,
            headers=headers,
            timeout=10
        )
        print(f"✅ Webhook response ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Failed to send webhook: {e}")


def generate_episode_keyframes(episode_num: int):
    """Generate all key moments for an episode."""
    episode = EPISODES.get(episode_num)
    if not episode:
        print(f"Episode {episode_num} not defined yet.")
        return []

    print(f"\n🎬 Generating keyframes for Episode {episode_num}: {episode['title']}")
    print(f"Focus: {episode['focus']}\n")

    moments = [
        "Wide establishing shot with god rays",
        "Medium shot - runes beginning to glow / ruins reacting",
        "Hero close-up - eyes open, staff rising",
        "Climactic energy explosion / vision moment"
    ]

    keyframes = []
    for i, moment in enumerate(moments, 1):
        prompt = generate_keyframe_prompt(episode_num, moment)
        keyframe = {
            "episode": episode_num,
            "moment": i,
            "description": moment,
            "prompt": prompt
        }
        keyframes.append(keyframe)
        print(f"  Keyframe {i}: {moment}")
        # In real use: send this prompt to Kling AI / Grok Imagine here

    return keyframes


# ==================== MAIN WORKFLOW ====================

def run_workflow(episode_num: int, auto_send_webhook: bool = True):
    print("=" * 60)
    print(f"🚀 Starting Abyss Masterpiece Workflow - Episode {episode_num}")
    print("=" * 60)

    # Step 1: Generate consistent keyframes
    keyframes = generate_episode_keyframes(episode_num)

    # Step 2: Prepare Kling AI video prompt (simplified)
    episode = EPISODES.get(episode_num, {})
    video_prompt = f"""Cinematic vertical 9:16 video for Episode {episode_num}: {episode.get('title', '')}.
{episode.get('focus', '')}

Use the exact same wizard from the keyframes. Slow cinematic push-in, 
powerful energy effects, teal-orange color grade, shallow depth of field.
"""

    print("\n🎥 Prepared Kling AI Video Prompt:")
    print(video_prompt[:200] + "...")

    # Step 3: (In real system) Call Kling AI here
    print("\n📤 (Placeholder) Sending prompts to Kling AI for video generation...")

    # Step 4: Send completion event to webhook
    if auto_send_webhook:
        webhook_payload = {
            "episode": episode_num,
            "title": episode.get("title"),
            "keyframes_generated": len(keyframes),
            "video_prompt_ready": True,
            "status": "ready_for_video_generation"
        }
        print("\n📡 Sending event to secure webhook...")
        send_to_webhook("new_episode_ready", webhook_payload)

    print("\n✅ Workflow completed successfully!")
    print("Next steps in real system:")
    print("  - Generate video with Kling AI using the prepared prompt")
    print("  - When video is ready → call webhook again with video_url")
    print("  - Webhook triggers: auto caption generation + TikTok upload")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Abyss Masterpiece Content Workflow")
    parser.add_argument("--episode", type=int, required=True, help="Episode number to generate")
    parser.add_argument("--no-webhook", action="store_true", help="Skip sending to webhook")
    args = parser.parse_args()

    run_workflow(args.episode, auto_send_webhook=not args.no_webhook)