/**
 * Cloudflare Worker — Maintenance page for ladiaria.com.uy
 *
 * HOW TO ACTIVATE MAINTENANCE:
 *   Cloudflare Dashboard → Workers & Pages → maintenance-ladiaria
 *   → Settings → Triggers → add route: ladiaria.com.uy/*
 *
 * HOW TO DEACTIVATE:
 *   Remove (or disable) that route. Zero code changes needed.
 *
 * BYPASS (for the deploy team):
 *   Visit https://ladiaria.com.uy/?bypass=Pqerd9jHOjohgYYoxkPj8A
 *   A cookie is set automatically — all subsequent pages work normally for 24h.
 *   Share the full URL with the team via Slack before starting the deploy.
 */

const BYPASS_TOKEN = "Pqerd9jHOjohgYYoxkPj8A";

const MAINTENANCE_HTML = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>la diaria — Ya volvemos</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      background: #f4f4f4;
      color: #1a1a1a;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    header {
      background: #ffffff;
      border-bottom: 1px solid #e0e0e0;
      padding: 18px 24px;
      text-align: center;
    }

    .logo {
      font-size: 1.5rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #1a1a1a;
    }

    main {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-start;
      padding: 80px 24px 40px;
      text-align: center;
    }

    h1 {
      font-size: 2.2rem;
      font-weight: 800;
      color: #1a1a1a;
      margin-bottom: 0.75rem;
      line-height: 1.2;
    }

    p {
      font-size: 1.2rem;
      color: #333333;
      line-height: 1.6;
    }

    footer {
      border-top: 1px solid #e0e0e0;
      padding: 20px 24px;
      text-align: center;
    }

    footer p {
      font-size: 0.875rem;
      color: #666666;
      line-height: 1.6;
    }

    footer strong {
      color: #444444;
    }

    footer a {
      color: #666666;
    }

    @media (max-width: 600px) {
      h1 { font-size: 1.75rem; }
      p { font-size: 1rem; }
      main { padding-top: 60px; }
    }
  </style>
</head>
<body>
  <header>
    <div class="logo">la diaria</div>
  </header>
  <main>
    <h1>Ya volvemos</h1>
    <p>Estamos actualizando el sitio.</p>
  </main>
  <footer>
    <p><strong>¿Tenés consultas?</strong><br>
    Visitá nuestro <a href="https://ayuda.ladiaria.com.uy/">centro de ayuda</a> o <a href="https://ayuda.ladiaria.com.uy/contacto/">contactanos</a>.</p>
  </footer>
</body>
</html>`;

export default {
  async fetch(request, env) {
    const token = env.BYPASS_TOKEN || BYPASS_TOKEN;
    const url = new URL(request.url);

    // Check bypass token in query string (?bypass=TOKEN)
    if (url.searchParams.get("bypass") === token) {
      // Pass through to origin and set a bypass cookie so subsequent pages work too
      const originResponse = await fetch(request);
      const response = new Response(originResponse.body, originResponse);
      response.headers.append(
        "Set-Cookie",
        `bypass=${token}; Path=/; Max-Age=86400; Secure; SameSite=Lax`
      );
      return response;
    }

    // Check bypass cookie (set on first visit with ?bypass=TOKEN)
    const cookieHeader = request.headers.get("Cookie") || "";
    if (cookieHeader.includes(`bypass=${token}`)) {
      return fetch(request);
    }

    // Everyone else sees the maintenance page
    return new Response(MAINTENANCE_HTML, {
      status: 503,
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "Retry-After": "3600",
        "Cache-Control": "no-store, no-cache",
      },
    });
  },
};
