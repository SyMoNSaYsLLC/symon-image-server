const terminalEl = document.getElementById("terminal");
const term = new Terminal({ cursorBlink: true, convertEol: true, fontFamily: "monospace", fontSize: 14 });
term.open(terminalEl);

const protocol = window.location.protocol === "https:" ? "wss" : "ws";
const ws = new WebSocket(`${protocol}://${window.location.host}/api/terminal/ws`);

ws.addEventListener("open", () => {
  term.write("Connected to Symoneural terminal\r\n");
});

ws.addEventListener("message", (event) => {
  term.write(event.data);
});

ws.addEventListener("close", () => {
  term.write("\r\n[terminal disconnected]\r\n");
});

term.onData((data) => {
  if (ws.readyState === WebSocket.OPEN) ws.send(data);
});
