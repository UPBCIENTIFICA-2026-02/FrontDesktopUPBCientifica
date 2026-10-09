// ============================================================================
// MOCK del Authentication Service (SOAP) — SOLO PARA DESARROLLO DEL CLIENTE
// ============================================================================
// Este NO es el servicio real. Es un servidor falso que devuelve un token fijo
// para que el cliente móvil pueda probar el flujo Login → Home sin esperar a
// que Dev A tenga listo el Authentication Service real.
//
// >>> NOTA PARA EL PROGRAMADOR DEL SERVIDOR (Dev A) <
// El servicio real debe exponer estas mismas 3 operaciones por SOAP, con estos
// mismos nombres de campos, para que el cliente móvil no requiera cambios:
//   - login(usuario, contrasena, origenCliente) -> token, roles, mapaServiciosAutorizados
//   - validarToken(token) -> valido (true/false)
//   - logout(token) -> (sin cuerpo relevante)
// Si el WSDL real usa otros nombres/namespace, avísale al equipo de móvil para
// ajustar SoapClient.kt y AuthRepository.kt en consecuencia.
// ============================================================================

const http = require("http");

const PORT = 8080;
const NAMESPACE = "urn:upbcientifica-auth";

// "Base de datos" falsa de usuarios de prueba
const USUARIOS_VALIDOS = {
  user1: "1234",
  investigador: "test",
};

function leerCuerpo(req) {
  return new Promise((resolve) => {
    let data = "";
    req.on("data", (chunk) => (data += chunk));
    req.on("end", () => resolve(data));
  });
}

// Extrae el texto de una etiqueta del XML entrante (parser mínimo, suficiente para el mock)
function extraerTag(xml, tag) {
  const match = xml.match(new RegExp(`<[^>]*${tag}[^>]*>([^<]*)</[^>]*${tag}>`, "i"));
  return match ? match[1].trim() : null;
}

function respuestaSoap(operation, cuerpoInterno) {
  return `<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="${NAMESPACE}">
  <soap:Body>
    <ns:${operation}Response>
      ${cuerpoInterno}
    </ns:${operation}Response>
  </soap:Body>
</soap:Envelope>`;
}

const server = http.createServer(async (req, res) => {
  const body = await leerCuerpo(req);
  const soapAction = req.headers["soapaction"] || "";
  console.log(`\n[${new Date().toLocaleTimeString()}] SOAPAction: ${soapAction}`);

  res.setHeader("Content-Type", "text/xml; charset=utf-8");

  // --- login ---
  if (soapAction.includes("login")) {
    const usuario = extraerTag(body, "usuario");
    const contrasena = extraerTag(body, "contrasena");
    console.log(`  login → usuario="${usuario}"`);

    if (USUARIOS_VALIDOS[usuario] && USUARIOS_VALIDOS[usuario] === contrasena) {
      res.writeHead(200);
      res.end(
        respuestaSoap(
          "login",
          `<token>mock-token-${usuario}-abc123</token>
       <roles>investigador,usuario</roles>
       <mapaServiciosAutorizados>storage,sharedfile,streaming</mapaServiciosAutorizados>`
        )
      );
    } else {
      // Credenciales inválidas → devolvemos un fault SOAP
      res.writeHead(500);
      res.end(
        respuestaSoap("login", `<error>Credenciales inválidas</error>`)
      );
    }
    return;
  }

  // --- validarToken ---
  if (soapAction.includes("validarToken")) {
    const token = extraerTag(body, "token");
    const valido = token && token.startsWith("mock-token-");
    res.writeHead(200);
    res.end(respuestaSoap("validarToken", `<valido>${valido}</valido>`));
    return;
  }

  // --- logout ---
  if (soapAction.includes("logout")) {
    res.writeHead(200);
    res.end(respuestaSoap("logout", `<ok>true</ok>`));
    return;
  }

  // Operación no reconocida
  res.writeHead(400);
  res.end(respuestaSoap("error", `<error>Operación no reconocida</error>`));
});

server.listen(PORT, () => {
  console.log("========================================================");
  console.log(" MOCK Authentication Service corriendo");
  console.log(` http://localhost:${PORT}`);
  console.log(" Usuarios de prueba: user1/1234  |  investigador/test");
  console.log(" (Ctrl+C para detener)");
  console.log("========================================================");
});