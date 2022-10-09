import socket
import ssl
import sys
import tkinter

HSTEP, VSTEP = 13, 18
WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100


def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x >= WIDTH - HSTEP:
            cursor_x = HSTEP
            cursor_y += VSTEP
    return display_list


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
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c)

    def load(self, url):
        headers, body = request(url)
        text = lex(body)
        self.display_list = layout(text)
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


def lex(html: str):
    inside_tag = False
    text = ""
    for ch in html:
        if ch == "<":
            inside_tag = True
        elif ch == ">":
            inside_tag = False
        elif not inside_tag:
            text += ch
    return text


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = URL.parse(sys.argv[1])
    else:
        url = URL.file("./index.html")
    Browser().load(url)
    tkinter.mainloop()
