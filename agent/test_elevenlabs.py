"""
Diagnostic script to test ElevenLabs TTS directly.
Run inside the agent container:
  docker compose exec agent python test_elevenlabs.py
"""
import asyncio
import json
import os
import sys

import aiohttp

API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID = sys.argv[1] if len(sys.argv) > 1 else "kPzsL2i3teMYv0FxEYQ6"
MODEL = sys.argv[2] if len(sys.argv) > 2 else "eleven_multilingual_v2"
TEXT = "Привет! Я виртуальный ассистент."

BASE_URL = "https://api.elevenlabs.io/v1"


async def test_user_info():
    """1. Verify API key"""
    print("=== 1. Checking API key ===")
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/user", headers={"xi-api-key": API_KEY}
        ) as resp:
            print(f"Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"User: {data.get('first_name', 'N/A')} (tier: {data.get('subscription', {}).get('tier', 'N/A')})")
                chars = data.get("subscription", {}).get("character_count", 0)
                limit = data.get("subscription", {}).get("character_limit", 0)
                print(f"Characters used: {chars}/{limit}")
            else:
                print(f"ERROR: {await resp.text()}")
                return False
    return True


async def test_voice_info():
    """2. Check if voice exists"""
    print(f"\n=== 2. Checking voice {VOICE_ID} ===")
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/voices/{VOICE_ID}",
            headers={"xi-api-key": API_KEY},
        ) as resp:
            print(f"Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"Voice: {data.get('name')} (category: {data.get('category')})")
                print(f"Labels: {data.get('labels', {})}")
            else:
                print(f"ERROR: {await resp.text()}")
                return False
    return True


async def test_rest_tts():
    """3. Test REST TTS endpoint"""
    print(f"\n=== 3. REST TTS (model={MODEL}) ===")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/text-to-speech/{VOICE_ID}/stream?model_id={MODEL}&output_format=pcm_24000",
            headers={"xi-api-key": API_KEY, "Content-Type": "application/json"},
            json={"text": TEXT, "model_id": MODEL},
        ) as resp:
            print(f"Status: {resp.status}")
            print(f"Content-Type: {resp.content_type}")
            if resp.status == 200:
                data = await resp.read()
                print(f"Audio size: {len(data)} bytes")
                if len(data) > 0:
                    print("SUCCESS: Audio received!")
                else:
                    print("ERROR: Empty audio response")
            else:
                print(f"ERROR: {await resp.text()}")
                return False
    return True


async def test_websocket_tts():
    """4. Test WebSocket multi-stream TTS endpoint"""
    print(f"\n=== 4. WebSocket multi-stream TTS ===")
    ws_url = (
        f"wss://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/multi-stream-input?"
        f"model_id={MODEL}&output_format=pcm_24000"
        f"&enable_ssml_parsing=false&enable_logging=true"
        f"&inactivity_timeout=180&apply_text_normalization=auto"
        f"&sync_alignment=true&auto_mode=true"
    )
    print(f"URL: {ws_url[:100]}...")

    context_id = "test-ctx-001"
    audio_chunks = 0
    total_audio_bytes = 0
    got_error = False

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                ws_url, headers={"xi-api-key": API_KEY}
            ) as ws:
                print("WebSocket connected!")

                # Init packet
                init_pkt = {"text": " ", "voice_settings": {}, "context_id": context_id}
                await ws.send_json(init_pkt)
                print(f"Sent init: {json.dumps(init_pkt)}")

                # Text packet with flush
                text_pkt = {"text": f"{TEXT} ", "context_id": context_id, "flush": True}
                await ws.send_json(text_pkt)
                print(f"Sent text: {json.dumps(text_pkt)}")

                # Close context
                close_pkt = {"context_id": context_id, "close_context": True}
                await ws.send_json(close_pkt)
                print(f"Sent close: {json.dumps(close_pkt)}")

                # Read responses
                print("\nReceiving responses:")
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        ctx = data.get("contextId", "?")

                        if data.get("error"):
                            print(f"  ERROR: {data['error']}")
                            got_error = True
                            break

                        has_audio = bool(data.get("audio"))
                        is_final = data.get("isFinal", False)
                        alignment = bool(data.get("normalizedAlignment") or data.get("alignment"))

                        if has_audio:
                            import base64
                            audio_bytes = len(base64.b64decode(data["audio"]))
                            audio_chunks += 1
                            total_audio_bytes += audio_bytes
                            if audio_chunks <= 3:
                                print(f"  Audio chunk #{audio_chunks}: {audio_bytes} bytes (ctx={ctx})")
                            elif audio_chunks == 4:
                                print(f"  ... (more chunks)")

                        if is_final:
                            print(f"  isFinal=true (ctx={ctx})")
                            break

                        if not has_audio and not is_final:
                            # Print first few non-audio messages
                            keys = [k for k in data.keys() if k != "contextId"]
                            print(f"  Non-audio msg: keys={keys} (ctx={ctx})")

                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSE):
                        print("  WebSocket closed by server")
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"  WebSocket error: {ws.exception()}")
                        break

                print(f"\nTotal: {audio_chunks} chunks, {total_audio_bytes} bytes")
                if audio_chunks > 0 and not got_error:
                    print("SUCCESS: WebSocket TTS works!")
                    return True
                else:
                    print("FAILURE: No audio received via WebSocket")
                    return False

    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
        return False


async def test_websocket_single_stream():
    """5. Test single-stream WebSocket as fallback"""
    print(f"\n=== 5. WebSocket single-stream TTS ===")
    ws_url = (
        f"wss://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream-input?"
        f"model_id={MODEL}&output_format=pcm_24000"
    )
    print(f"URL: {ws_url[:100]}...")

    audio_chunks = 0
    total_audio_bytes = 0

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                ws_url, headers={"xi-api-key": API_KEY}
            ) as ws:
                print("WebSocket connected!")

                # BOS (beginning of stream)
                bos = {
                    "text": " ",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                    "generation_config": {"chunk_length_schedule": [120, 160, 250, 290]},
                }
                await ws.send_json(bos)
                print("Sent BOS")

                # Text
                await ws.send_json({"text": TEXT})
                print(f"Sent text: {TEXT}")

                # EOS (end of stream)
                await ws.send_json({"text": ""})
                print("Sent EOS")

                # Read responses
                print("\nReceiving responses:")
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)

                        if data.get("error"):
                            print(f"  ERROR: {data}")
                            break

                        has_audio = bool(data.get("audio"))
                        is_final = data.get("isFinal", False)

                        if has_audio:
                            import base64
                            audio_bytes = len(base64.b64decode(data["audio"]))
                            audio_chunks += 1
                            total_audio_bytes += audio_bytes
                            if audio_chunks <= 3:
                                print(f"  Audio chunk #{audio_chunks}: {audio_bytes} bytes")

                        if is_final:
                            print(f"  isFinal=true")
                            break

                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSE):
                        print("  WebSocket closed")
                        break

                print(f"\nTotal: {audio_chunks} chunks, {total_audio_bytes} bytes")
                if audio_chunks > 0:
                    print("SUCCESS!")
                    return True
                else:
                    print("FAILURE: No audio")
                    return False
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
        return False


async def main():
    if not API_KEY:
        print("ERROR: ELEVENLABS_API_KEY not set")
        sys.exit(1)

    print(f"Voice ID: {VOICE_ID}")
    print(f"Model: {MODEL}")
    print(f"Text: {TEXT}")
    print(f"API Key: ...{API_KEY[-4:]}")
    print()

    ok = await test_user_info()
    if not ok:
        return

    ok = await test_voice_info()
    if not ok:
        return

    await test_rest_tts()
    await test_websocket_tts()
    await test_websocket_single_stream()


if __name__ == "__main__":
    asyncio.run(main())
