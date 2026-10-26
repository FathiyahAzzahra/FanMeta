# Image untuk Hugging Face Spaces (SDK: Docker).
# File model (.pt) TIDAK ikut di image; diunduh dari Hugging Face Hub saat container start.
FROM python:3.11-slim

# Spaces menjalankan container sebagai user dengan UID 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1
WORKDIR /home/user/app

# Default: torch versi CPU (image jauh lebih kecil, cocok untuk Space CPU gratis).
# Untuk Space GPU, isi variable TORCH_INDEX_URL=https://pypi.org/simple di Settings Space
# (torch dari PyPI untuk Linux sudah termasuk CUDA).
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user $(grep '^torch==' requirements.txt) --index-url "$TORCH_INDEX_URL" \
 && pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .
# Jaga-jaga jika start.sh tersimpan dengan baris Windows (CRLF).
RUN sed -i 's/\r$//' start.sh

EXPOSE 7860
CMD ["bash", "start.sh"]
