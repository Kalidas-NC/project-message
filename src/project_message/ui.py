"""Streamlit client: the user talks here; the server prints in its terminal."""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

import streamlit as st

DEFAULT_SERVER = "http://127.0.0.1:8765"


def post_message(server: str, from_number: str, text: str) -> dict:
    request = Request(
        f"{server.rstrip('/')}/messages",
        data=json.dumps({"from": from_number, "text": text}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode())


def main() -> None:
    st.set_page_config(page_title="Agent mock", layout="centered")
    st.title("User")
    st.caption("Client. Watch the server terminal for what the backend sees.")

    server = st.text_input("Server", DEFAULT_SERVER)
    from_number = st.text_input("My number", "+15551234567")

    if "log" not in st.session_state:
        st.session_state.log = []

    for entry in st.session_state.log:
        st.write(entry)

    text = st.chat_input("Type a message")
    if text:
        st.session_state.log.append(f"you: {text}")
        try:
            payload = post_message(server, from_number, text)
        except URLError:
            st.session_state.log.append("client: could not reach the server")
            st.rerun()

        if not payload.get("ok") and payload.get("reason") == "not_allowed":
            st.session_state.log.append("server: your number is not on the allowlist")
        else:
            for reply in payload.get("replies") or []:
                st.session_state.log.append(f"server: {reply['text']}")
        st.rerun()


if __name__ == "__main__":
    main()
