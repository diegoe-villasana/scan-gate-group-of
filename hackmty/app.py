import os
import requests
from flask import Flask, render_template, request, jsonify, Response
import pandas as pd
import joblib
from tensorflow import keras
from dotenv import load_dotenv
import time # <-- Para el simulador


load_dotenv() 

app = Flask(__name__)


print("Cargando modelo y preprocesador...")
MODEL_PATH = "model/prediccion_consumo_REAL_ADV_CORR_v1.keras"
PREPROC_PATH = "model/preprocesador_consumo_REAL_ADV_CORR_v1.joblib"
model = keras.models.load_model(MODEL_PATH)
preprocessor = joblib.load(PREPROC_PATH)
print("Modelos cargados.")

try:
    df_original = pd.read_csv("data/[HackMTY2025]_ConsumptionPrediction_Dataset_v1.csv")
    print("Datos cargados desde .csv")
except FileNotFoundError:
    print("ADVERTENCIA: No se encontró el .csv, intentando cargar el .xlsx...")
    df_original = pd.read_excel("data/[HackMTY2025]_ConsumptionPrediction_Dataset_v1.xlsx")
    print("Datos cargados desde .xlsx")



# TODO: Cuando estés listo, reemplaza estas funciones

estado_scanner = {
    "status": "waiting", 
    "message": "Esperando QR...",
    "qr_data": None,
    "vuelo_actual": "VUELO-SIMULADO-123",
    "drawer": "SIM-DRAWER-01",
    "current": 0,
    "capacity": 5
}

@app.route('/video_feed')
def video_feed():
    """
    Ruta que sirve el video en vivo.
    ¡Esta ruta ya no es necesaria si usamos una imagen estática!
    Pero la dejamos por si la necesitas en el futuro.
    """
    # TODO: Pega aquí tu lógica de 'cv2.VideoCapture'
    return Response("El streaming de video real debe ser implementado aquí", mimetype='text/plain')

@app.route('/vuelos_disponibles')
def vuelos_disponibles():
    """Ruta que le da al frontend la lista de vuelos."""
    # TODO: Reemplaza esto con tu lista real de vuelos
    print("Enviando lista de vuelos simulada...")
    return jsonify({"vuelos": ["VUELO-SIMULADO-123", "VUELO-REAL-456", "VUELO-TEST-789"]})

@app.route('/seleccionar_vuelo')
def seleccionar_vuelo():
    """Ruta que selecciona el vuelo actual."""
    global estado_scanner
    vuelo = request.args.get('vuelo')
    estado_scanner["vuelo_actual"] = vuelo
    print(f"Vuelo simulado seleccionado: {vuelo}")
    return jsonify({"message": f"Vuelo {vuelo} seleccionado."})

@app.route('/ultimo_qr')
def ultimo_qr():
    """Ruta que le da al frontend el último QR escaneado."""
    global estado_scanner
    
    if request.args.get('clear') == 'true':
        print("Limpiando estado del scanner (simulado)")
        estado_scanner["status"] = "waiting"
        estado_scanner["message"] = "Esperando QR..."
        estado_scanner["qr_data"] = None
        estado_scanner["current"] = 0
        return jsonify(estado_scanner)

    if estado_scanner["status"] == "waiting" and estado_scanner["current"] < estado_scanner["capacity"]:
        estado_scanner["status"] = "ok"
        estado_scanner["message"] = "QR Válido. Producto agregado."
        estado_scanner["current"] += 1
        estado_scanner["qr_data"] = {
            "drawer_id": "SIM-DRAWER-01",
            "flight_number": estado_scanner["vuelo_actual"],
            "total_drawer": 5,
            "drawer_category": "Bebidas",
            "customer_name": "Cliente Simulado",
            "expiry_date": "2025-12-31"
        }
    
    elif estado_scanner["current"] >= estado_scanner["capacity"]:
        estado_scanner["status"] = "full"
        estado_scanner["message"] = "¡Drawer lleno!"

    print(f"Enviando estado del scanner (simulado): {estado_scanner['status']}")
    return jsonify(estado_scanner)





@app.route("/")
def home():
    if df_original is None:
        return "Error: No se pudieron cargar los datos iniciales. Revisa los logs.", 500

    print("Procesando datos para la página de inicio...")
    df_analisis = df_original.copy()
    df_analisis['Product_Category'] = df_analisis['Product_ID'].str.slice(0,3)
    features = ['Origin', 'Flight_Type', 'Service_Type', 'Passenger_Count', 'Product_Category']
    X = preprocessor.transform(df_analisis[features])
    predicciones = model.predict(X).flatten()
    df_analisis['Predicted_Consumption'] = predicciones
    df_analisis['Predicted_Waste'] = df_analisis['Standard_Specification_Qty'] - df_analisis['Predicted_Consumption']
    df_analisis['Predicted_Waste'] = df_analisis['Predicted_Waste'].clip(lower=0)
    df_analisis['Waste_Percentage'] = (df_analisis['Predicted_Waste'] / df_analisis['Standard_Specification_Qty'] * 100).round(2)
    report = df_analisis[['Product_Name', 'Predicted_Waste', 'Waste_Percentage']].head(10).to_dict(orient='records')
    top_10_waste = df_analisis.nlargest(10, 'Predicted_Waste').sort_values('Predicted_Waste', ascending=False)
    chart1_data = {
        "labels": top_10_waste['Product_Name'].tolist(),
        "data": top_10_waste['Predicted_Waste'].round(2).tolist()
    }
    waste_by_category = df_analisis.groupby('Product_Category')['Predicted_Waste'].sum().sort_values(ascending=False)
    chart2_data = {
        "labels": waste_by_category.index.tolist(),
        "data": waste_by_category.round(2).tolist()
    }
    waste_by_flight = df_analisis.groupby('Flight_Type')['Predicted_Waste'].sum().sort_values(ascending=False)
    chart3_data = {
        "labels": waste_by_flight.index.tolist(),
        "data": waste_by_flight.round(2).tolist()
    }
    
    return render_template(
        "index.html", 
        report=report,
        chart1_data=chart1_data,
        chart2_data=chart2_data,
        chart3_data=chart3_data
    )


@app.route("/scanner")
def scanner_page():
    return render_template("scanner.html")



@app.route("/get_ai_explanation", methods=['POST'])
def get_ai_explanation():

    try:
        apiKey = os.environ.get("GEMINI_API_KEY")
        if not apiKey:
            return jsonify({"error": "API Key de Gemini no encontrada."}), 500
        apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={apiKey}"
        report_data = request.json.get('reportData', [])
        if not report_data:
            return jsonify({"error": "No se recibieron datos para analizar."}), 400
        dataString = "Aquí están los datos de predicción de desperdicio de productos:\n"
        for item in report_data:
            dataString += f"- Producto: {item['Product_Name']}, Desperdicio Predicho: {item['Predicted_Waste']}, Porcentaje de Ajuste: {item['Waste_Percentage']}%\n"
        systemPrompt = "Eres un asistente experto en logística y análisis de datos para aerolíneas. Tu trabajo es analizar los datos de predicción de desperdicio que te da el usuario y explicarle qué significan en un tono amigable, profesional y accionable. No repitas los datos, solo explícalos. Enfócate en las oportunidades de mejora."
        userQuery = f"Por favor, analiza los siguientes datos y dame un resumen de lo que significan. ¿Qué productos tienen más desperdicio? ¿Qué significa el '% Subir/Bajar'? ¿Qué acciones clave debería tomar basándome en esto?\n\nDatos:\n{dataString}"
        payload = {
            "contents": [{"parts": [{"text": userQuery}]}],
            "systemInstruction": {"parts": [{"text": systemPrompt}]},
        }
        response = requests.post(apiUrl, json=payload, timeout=30)
        response.raise_for_status() 
        result = response.json()
        candidate = result.get("candidates", [{}])[0]
        text_response = candidate.get("content", {}).get("parts", [{}])[0].get("text")
        if text_response:
            return jsonify({"explanation": text_response})
        else:
            return jsonify({"error": "Respuesta inesperada de la API de Gemini."}), 500
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error: {http_err} - {response.text}")
        return jsonify({"error": f"Error de la API de Gemini: {http_err}"}), 500
    except Exception as e:
        print(f"Error interno: {e}")
        return jsonify({"error": f"Error interno del servidor: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
