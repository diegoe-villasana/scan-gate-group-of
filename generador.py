import qrcode
import json

datos = {
    "drawer_id": "DRW_001",
    "flight_number": "LAK345",
    "total_drawer": 8,
    "drawer_category": "Snacks",
    "customer_name": "Delta Airlines",
    "expiry_date": "2025-12-10",
}

data = json.dumps(datos, ensure_ascii=False, indent=2)

img = qrcode.make(data)
img.save("qr_producto5_2_3_4.png")
print("QR generado: qr_producto.png")

