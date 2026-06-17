#!/usr/bin/env python3
"""
GreenNode Interview Assistant — Main Entry Point

Starts two servers:
1. WebSocket server (port 9090) — real-time transcription via MaaS
2. FastAPI HTTP server (port 8000) — web UI + assessment API + Excel download

Usage:
    python run_interview.py [options]

    # Minimal (uses env vars for MaaS config):
    python run_interview.py

    # With explicit config:
    python run_interview.py --maas-url https://your-endpoint --maas-key your-key
"""
import argparse
import json
import logging
import os
import sys
import threading
import time

import numpy as np
import uvicorn
from websockets.sync.server import serve as ws_serve
from websockets.exceptions import ConnectionClosed

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class SimpleClientManager:
    """Lightweight client manager — no dependency on whisper_live.server."""

    def __init__(self, max_clients=4, max_connection_time=3600):
        self.clients = {}
        self.start_times = {}
        self.max_clients = max_clients
        self.max_connection_time = max_connection_time

    def add_client(self, websocket, client):
        self.clients[websocket] = client
        self.start_times[websocket] = time.time()

    def get_client(self, websocket):
        return self.clients.get(websocket)

    def remove_client(self, websocket):
        client = self.clients.pop(websocket, None)
        if client:
            client.cleanup()
        self.start_times.pop(websocket, None)

    def is_server_full(self, websocket, options):
        if len(self.clients) >= self.max_clients:
            wait_time = self._get_wait_time()
            websocket.send(json.dumps({
                "uid": options.get("uid", ""),
                "status": "WAIT",
                "message": wait_time,
            }))
            return True
        return False

    def is_client_timeout(self, websocket):
        start = self.start_times.get(websocket)
        if start and (time.time() - start) >= self.max_connection_time:
            client = self.clients.get(websocket)
            if client:
                client.disconnect()
            return True
        return False

    def _get_wait_time(self):
        if not self.start_times:
            return 0
        min_remaining = min(
            self.max_connection_time - (time.time() - t)
            for t in self.start_times.values()
        )
        return max(0, min_remaining / 60)


def start_whisper_server(args):
    """Start WebSocket server with MaaS backend (no local Whisper needed)."""
    from whisper_live.backend.maas_backend import ServeClientMaaS

    client_manager = SimpleClientManager(
        max_clients=args.max_clients,
        max_connection_time=args.max_connection_time,
    )

    def recv_audio(websocket):
        """Handle a single WebSocket client connection."""
        client = None
        try:
            logger.info("New client connected")
            options = websocket.recv()
            options = json.loads(options)

            if client_manager.is_server_full(websocket, options):
                websocket.close()
                return

            client = ServeClientMaaS(
                websocket=websocket,
                task=options.get("task", "transcribe"),
                language=options.get("language"),
                client_uid=options.get("uid"),
                initial_prompt=options.get("initial_prompt"),
                vad_parameters=options.get("vad_parameters"),
                use_vad=options.get("use_vad", True),
                send_last_n_segments=options.get("send_last_n_segments", 10),
                no_speech_thresh=options.get("no_speech_thresh", 0.45),
                clip_audio=options.get("clip_audio", False),
                same_output_threshold=options.get("same_output_threshold", 10),
                maas_base_url=args.maas_url,
                maas_api_key=args.maas_key,
                maas_model=args.maas_model,
            )
            client_manager.add_client(websocket, client)

            frame_count = 0
            while not client_manager.is_client_timeout(websocket):
                frame_data = websocket.recv()
                if frame_data == b"END_OF_AUDIO" or (
                    isinstance(frame_data, str) and "END_OF_AUDIO" in frame_data
                ):
                    logger.info("Received END_OF_AUDIO")
                    break

                if isinstance(frame_data, str):
                    logger.warning(f"Received text frame (expected binary): {frame_data[:100]}")
                    continue

                frame_np = np.frombuffer(frame_data, dtype=np.float32)
                client.add_frames(frame_np)
                frame_count += 1
                if frame_count % 100 == 0:
                    logger.info(f"Received {frame_count} audio frames ({len(frame_np)} samples each)")

        except ConnectionClosed as e:
            logger.info(f"Connection closed by client: {e}")
        except json.JSONDecodeError:
            logger.error("Failed to decode client config JSON")
        except Exception as e:
            logger.error(f"Error in recv_audio: {e}", exc_info=True)
        finally:
            if client_manager.get_client(websocket):
                client_manager.remove_client(websocket)
            try:
                websocket.close()
            except Exception:
                pass

    logger.info(f"Starting WebSocket server on ws://0.0.0.0:{args.ws_port}")
    with ws_serve(
        recv_audio, "0.0.0.0", args.ws_port,
        ping_interval=30,    # Send ping every 30s
        ping_timeout=120,    # Wait 2min for pong (generous for slow connections)
        close_timeout=10,
        max_size=10 * 1024 * 1024,  # 10MB max message (for large audio chunks)
    ) as ws_server:
        ws_server.serve_forever()


def start_http_server(args):
    """Start FastAPI HTTP server for web UI + assessment API."""
    from interview.app import create_app

    output_dir = os.path.join(os.path.dirname(__file__), "output")
    app = create_app(output_dir=output_dir)

    logger.info(f"Starting Interview HTTP server on http://0.0.0.0:{args.http_port}")
    uvicorn.run(app, host="0.0.0.0", port=args.http_port, log_level="info")


def main():
    parser = argparse.ArgumentParser(description="GreenNode Interview Assistant")

    # MaaS config
    parser.add_argument("--maas-url", default=os.getenv("WHISPER_BASE_URL", ""),
                        help="VNGCloud MaaS Whisper API base URL")
    parser.add_argument("--maas-key", default=os.getenv("WHISPER_API_KEY", ""),
                        help="VNGCloud MaaS API key")
    parser.add_argument("--maas-model", default=os.getenv("WHISPER_MODEL", "openai/whisper-large-v3"),
                        help="Whisper model name on MaaS")

    # Server ports
    parser.add_argument("--ws-port", type=int, default=9090,
                        help="WhisperLive WebSocket port (default: 9090)")
    parser.add_argument("--http-port", type=int, default=8000,
                        help="HTTP server port for web UI (default: 8000)")

    # Client config
    parser.add_argument("--max-clients", type=int, default=4,
                        help="Max concurrent WebSocket clients")
    parser.add_argument("--max-connection-time", type=int, default=7200,
                        help="Max connection time in seconds (default: 7200 = 2 hours)")

    args = parser.parse_args()

    if not args.maas_url:
        logger.error("WHISPER_BASE_URL is required. Set via --maas-url or .env file.")
        sys.exit(1)

    # Start WebSocket server in a background thread
    ws_thread = threading.Thread(target=start_whisper_server, args=(args,), daemon=True)
    ws_thread.start()

    # Start HTTP server in the main thread
    start_http_server(args)


if __name__ == "__main__":
    main()
