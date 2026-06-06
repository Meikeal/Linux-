#!/usr/bin/env python3
"""Threaded static file server for the deployed blog."""

import argparse
import http.server
import os
import socketserver
from pathlib import Path


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    parser = argparse.ArgumentParser(description="Serve web-blog static files")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=80)
    parser.add_argument("--directory", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()

    os.chdir(args.directory)
    handler = http.server.SimpleHTTPRequestHandler

    with ThreadedTCPServer((args.host, args.port), handler) as server:
        print("Serving {} on {}:{}".format(args.directory, args.host, args.port), flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
