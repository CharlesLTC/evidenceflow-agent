import httpx


class Backend:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def request(self, method, path, **kwargs):
        with httpx.Client(timeout=240, trust_env=False) as client:
            response = client.request(method, self.base_url + path, **kwargs)
        if response.status_code == 503:
            data = response.json()
            if "trace_id" in data:
                return data  # A real controlled failure result is displayed as a failure.
        response.raise_for_status()
        return response.json()

    def ask(self, question, mode, session_id, fail_search_count=0):
        return self.request(
            "POST",
            "/ask",
            json={
                "question": question,
                "mode": mode,
                "session_id": session_id,
                "fail_search_count": fail_search_count,
            },
        )
