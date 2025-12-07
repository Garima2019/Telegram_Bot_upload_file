# mock_telegram.py
# Simple mock of Telegram file endpoints for local testing.

from flask import Flask, jsonify, send_file, abort, request
import io

app = Flask(__name__)

# File mapping: file_id -> file_path
FILE_MAP = {
    "FILE123": "documents/testfile.jpg",
    "FILE_PNG": "documents/testimage.png",
}

@app.route("/bot<token>/getFile")
def get_file(token):
    file_id = request.args.get("file_id")
    if not file_id or file_id not in FILE_MAP:
        return jsonify({"ok": False, "error": "file_id not found"}), 404
    file_path = FILE_MAP[file_id]
    # Respond like Telegram getFile
    return jsonify({"ok": True, "result": {"file_path": file_path}})

@app.route("/file/bot<token>/<path:fp>")
def file_download(token, fp):
    # Serve some bytes. For demo we return a tiny PNG generated in-memory.
    if fp.endswith(".jpg") or fp.endswith(".png"):
        # Generate a tiny 1x1 PNG in memory (binary)
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDAT\x08\xd7c\xf8\x0f\x00"
            b"\x01\x01\x01\x00\x18\xdd\x02\xfe\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return send_file(io.BytesIO(png_bytes), mimetype="image/png", as_attachment=False, attachment_filename=fp)
    # fallback: not found
    abort(404)

if __name__ == "__main__":
    # Runs on http://localhost:8080
    app.run(host="0.0.0.0", port=8080, debug=True)
