import socket
import ssl
import sys

def request(url):
    scheme, url = url.split("://", 1)
    assert scheme in ["http", "https"], "Unknown scheme {}".format(scheme)

    host, path = url.split("/", 1)
    path = "/" + path

    s = socket.socket(
        family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
    )

    port = 80 if scheme == "http" else 443

    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)

    if scheme == "https":
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=host)

    s.connect((host, port))
    s.send(
        "GET {} HTTP/1.1\r\n".format(path).encode("utf8")
        + "Host: {}\r\n".format(host).encode("utf8")
        + "Connection: close\r\n\r\n".encode("utf8")
    )

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


def print_content(body: str):
    inside_tag = False
    for ch in body:
        if ch == "<":
            inside_tag = True
        elif ch == ">":
            inside_tag = False
        elif not inside_tag:
            print(ch, end="")


if __name__ == "__main__":
    headers, body = request(sys.argv[1])
    print(headers)
    print_content(body)
