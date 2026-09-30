import os
import sys
import socket
import uvicorn
import qrcode

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def print_welcome_banner(ip: str, port: int):
    local_url = f"http://localhost:{port}"
    iphone_url = f"http://{ip}:{port}"

    print("=" * 60)
    print("  🌿  VOZ & HORAS | Gestor Diário de Trabalho  🌿")
    print("=" * 60)
    print(f"\n💻 No Computador:  {local_url}")
    print(f"📱 No iPhone:      {iphone_url}\n")
    print("--- APONTA A CÂMARA DO IPHONE PARA ESTE QR CODE ---")
    
    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(iphone_url)
        qr.print_ascii(invert=True)
    except Exception:
        print(f"(Acede manualmente pelo Safari do iPhone em: {iphone_url})")

    print("\n💡 Dica no iPhone: No Safari, toca no botão de Partilhar e escolhe")
    print("   'Adicionar ao Ecrã Principal' para usar como uma App real!\n")
    print("=" * 60)
    print("Pressiona CTRL + C para desligar o servidor.\n")

if __name__ == "__main__":
    ip = get_local_ip()
    port = 8000
    print_welcome_banner(ip, port)
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False, log_level="info")
