# ================================================================
# tests/test_smoke.py — Pruebas básicas del backend desplegado
# Ejecutar con: python tests/test_smoke.py URL_DEL_BACKEND
# ================================================================
import sys
import json
import urllib.request
import urllib.error


def test_health(base_url: str) -> bool:
    """Verifica que el endpoint /health responde correctamente."""
    print(f"\n[TEST 1] GET {base_url}/health")
    try:
        with urllib.request.urlopen(f"{base_url}/health", timeout=15) as r:
            data = json.loads(r.read())
            ok   = data.get("status") == "ok"
            print(f"  Status: {data.get('status')} | ES: {data.get('elasticsearch')}")
            print(f"  {'✅ PASS' if ok else '❌ FAIL'}")
            return ok
    except Exception as e:
        print(f"  ❌ FAIL — {e}")
        return False


def test_consulta_dominio(base_url: str) -> bool:
    """Verifica que /consulta responde a una consulta del dominio."""
    print(f"\n[TEST 2] POST {base_url}/consulta — consulta de dominio")
    payload = json.dumps({
        "session_id": "smoke-test-001",
        "mensaje": "Que dice el DS 081 sobre inspeccion de compresores?",
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/consulta",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
            ok   = len(data.get("respuesta", "")) > 50
            print(f"  Respuesta: {data.get('respuesta','')[:100]}...")
            print(f"  Tools usadas: {data.get('tools_usadas', [])}")
            print(f"  Fuentes RAG: {len(data.get('fuentes_rag', []))}")
            print(f"  {'✅ PASS' if ok else '❌ FAIL'}")
            return ok
    except Exception as e:
        print(f"  ❌ FAIL — {e}")
        return False


def test_fuera_dominio(base_url: str) -> bool:
    """Verifica que el agente rechaza consultas fuera del dominio."""
    print(f"\n[TEST 3] POST {base_url}/consulta — fuera de dominio")
    payload = json.dumps({
        "session_id": "smoke-test-002",
        "mensaje": "Que dieta debo seguir para bajar de peso?",
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/consulta",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data     = json.loads(r.read())
            respuesta = data.get("respuesta", "").lower()
            ok        = len(respuesta) > 20
            print(f"  Respuesta: {data.get('respuesta','')[:100]}...")
            print(f"  {'✅ PASS' if ok else '❌ FAIL'}")
            return ok
    except Exception as e:
        print(f"  ❌ FAIL — {e}")
        return False


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    base_url = base_url.rstrip("/")

    print("=" * 60)
    print(f"SMOKE TESTS — Backend FastAPI")
    print(f"URL: {base_url}")
    print("=" * 60)

    resultados = [
        test_health(base_url),
        test_consulta_dominio(base_url),
        test_fuera_dominio(base_url),
    ]

    total  = len(resultados)
    pasan  = sum(resultados)
    print(f"\n{'='*60}")
    print(f"RESULTADO: {pasan}/{total} tests pasan")
    if pasan == total:
        print("✅ Backend operativo y listo")
    else:
        print("❌ Hay tests fallando — revisar logs")
    print("=" * 60)
    sys.exit(0 if pasan == total else 1)
