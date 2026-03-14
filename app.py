from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageEnhance
from datetime import datetime
import subprocess
import os
import tempfile
import base64
import io
import sys
import os

POTRACE = os.path.join(os.path.dirname(__file__), "bin", "potrace")

app = Flask(__name__, static_folder=".", static_url_path="")

@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/process", methods=["POST"])
def process():
    file = request.files.get("image")
    threshold = int(request.form.get("threshold", 135))
    opttolerance = float(request.form.get("opttolerance", 2.0))
    turdsize = int(request.form.get("turdsize", 10))

    if not file:
        return jsonify({"error": "No image provided"}), 400

    img = Image.open(file.stream)

    # grayscale
    filter_ = ImageEnhance.Color(img)
    img = filter_.enhance(0)

    # slider: threshold filter
    img = img.convert("L")
    img = img.point(lambda p: 0 if p < threshold else 255)

    # crop image to 1:1
    w, h = img.size
    size = min(w, h)
    left = (w - size) // 2
    top = (h - size) // 2
    img = img.crop((left, top, left + size, top + size))

    # downscale image
    img.thumbnail((1500, 1500), Image.LANCZOS)

    # build preview
    preview_buf = io.BytesIO()
    img.save(preview_buf, format="PNG")
    preview_b64 = base64.b64encode(preview_buf.getvalue()).decode("utf-8")

    #get files
    tmpdir = tempfile.mkdtemp()
    bmp_path = os.path.join(tmpdir, "temp.bmp")
    dxf_path = os.path.join(tmpdir, "output.dxf")

    img.save(bmp_path)

    #run potrace for dxf
    result = subprocess.run([
        #"potrace",
        POTRACE,
        bmp_path,
        "--backend", "dxf",
        "--turdsize", str(turdsize),
        "--alphamax", "1.5",
        "--opttolerance", str(opttolerance),
        "--output", dxf_path,
    ], capture_output=True)

    if result.returncode != 0:
        return jsonify({"error": result.stderr.decode()}), 500

    # append datetime to filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output_{timestamp}.dxf"

    with open(dxf_path, "r") as f:
        dxf_content = f.read()

    return jsonify({
        "filename": filename,
        "dxf": dxf_content,
        "preview": preview_b64,
    })

if __name__ == "__main__":
    # app.run(debug=True, port=8080)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
