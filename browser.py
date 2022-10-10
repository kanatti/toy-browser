from dataclasses import dataclass
import socket
import ssl
import sys
import tkinter
import tkinter.font
from typing import List

HSTEP, VSTEP = 13, 18
WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100


@dataclass
class Text:
    text: str


@dataclass
class Tag:
    tag: str


Token = Text | Tag


class Layout:
    def __init__(self, tokens: List[Token]):
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 16
        for token in tokens:
            self.process_token(token)

    def process_token(self, token):
        if isinstance(token, Text):
            self.process_text(token)
        elif token.tag == "i":
            self.style = "italic"
        elif token.tag == "/i":
            self.style = "roman"
        elif token.tag == "b":
            self.weight = "bold"
        elif token.tag == "/b":
            self.weight = "normal"

    def process_text(self, token):
        font = tkinter.font.Font(
            size=self.size,
            weight=self.weight,
            slant=self.style,
        )
        for word in token.text.split():
            w = font.measure(word)
            if self.cursor_x + w >= WIDTH - HSTEP:
                self.cursor_y += font.metrics("linespace") * 1.25
                self.cursor_x = HSTEP
            self.display_list.append((self.cursor_x, self.cursor_y, word, font))
            self.cursor_x += w + font.measure(" ")


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.window.title("toybrowser")
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack()
        self.display_list = []
        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)

    def draw(self):
        self.canvas.delete("all")
        for x, y, word, font in self.display_list:
            if y > self.scroll + HEIGHT:
                continue
            if y + VSTEP < self.scroll:
                continue
            self.canvas.create_text(
                x, y - self.scroll, text=word, font=font, anchor="nw"
            )

    def load(self, url):
        headers, body = request(url)
        tokens = lex(body)
        self.display_list = Layout(tokens).display_list
        self.draw()

    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()

    def scrollup(self, e):
        self.scroll -= SCROLL_STEP
        self.draw()


class URL:
    def __init__(self, scheme, host, path, port):
        self.scheme = scheme
        self.host = host
        self.path = path
        self.port = port

    @staticmethod
    def parse(raw_url: str):
        scheme, url = raw_url.split("://", 1)
        assert scheme in ["file", "http", "https"], "Unknown scheme {}".format(scheme)

        host, path = url.split("/", 1)
        path = "/" + path
        port = 80 if scheme == "http" else 443

        if ":" in host:
            host, port = host.split(":", 1)
            port = int(port)

        return URL(scheme, host, path, port)

    @staticmethod
    def file(path: str):
        return URL("file", "", path, 0)


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
        req_body = req_body + "{}: {}\r\n".format(key, req_headers[key]).encode("utf8")

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


def lex(html: str) -> List[Token]:
    tokens = []
    in_tag = False
    text = ""
    for c in html:
        if c == "<":
            in_tag = True
            if text:
                tokens.append(Text(text))
            text = ""
        elif c == ">":
            in_tag = False
            tokens.append(Tag(text))
            text = ""
        else:
            text += c
    if not in_tag and text:
        tokens.append(Text(text))
    return tokens


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = URL.parse(sys.argv[1])
    else:
        url = URL.file("./index.html")
    Browser().load(url)
    tkinter.mainloop()
