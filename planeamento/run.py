from waitress import serve
from app import app   # substitui 'app' pelo nome do teu ficheiro Flask, se diferente

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000, threads=8)
