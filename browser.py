import socket
import ssl
import sys

class URL:
    def __init__(self, raw_url: str):
        scheme, url = raw_url.split("://", 1)
        assert scheme in ["file", "http", "https"], "Unknown scheme {}".format(scheme)

        host, path = url.split("/", 1)
        path = "/" + path
        port = 80 if scheme == "http" else 443


        if ":" in host:
            host, port = host.split(":", 1)
            port = int(port)

        self.scheme = scheme
        self.host = host
        self.path = path
        self.port = port
        


def request_file(url: URL):
    with open(url.path, "r") as f:
        body = f.read()
    return {}, body

def request_remote(url: URL):
    s = socket.socket(
        family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
    )

    if url.scheme == "https":
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=url.host)

    s.connect((url.host, url.port))

    req_headers = {"Host": url.host, "Connection": "close", "User-Agent": "toybrowser"}
    req_body = "GET {} HTTP/1.1\r\n".format(url.path).encode("utf8")
    for key in req_headers:
        req_body = req_body + "{}: {}\r\n".format(key, req_headers[key]).encode(
            "utf8"
        )

    req_body = req_body + "\r\n".encode("utf8")

    print("making request")
    print(req_body.decode("utf8"))

    s.send(req_body)

    response = s.makefile("r", encoding="utf8", newline="\r\n")

    statusline = response.readline()
    version, status, explanation = statusline.split(" ", 2)
    assert status == "200", "{}: {}".format(status, explanation)

    headers = {}
    while True:
        line = response.readline()
        if line == "\r\n":
            break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()

    assert "transfer-encoding" not in headers
    assert "content-encoding" not in headers

    body = response.read()
    s.close()

    return headers, body

def request(url: URL):
    if url.scheme == "file":
        return request_file(url)
    else:
        return request_remote(url)

def print_html(html: str):
    inside_tag = False
    for ch in html:
        if ch == "<":
            inside_tag = True
        elif ch == ">":
            inside_tag = False
        elif not inside_tag:
            print(ch, end="")


if __name__ == "__main__":
    url = URL(sys.argv[1])
    headers, body = request(url)
    print(headers)
    print_html(body)
