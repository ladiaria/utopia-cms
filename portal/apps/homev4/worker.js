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
    @font-face {
      font-family: "Dialect Gothic A";
      font-style: normal;
      font-weight: 400;
      src: url("https://ladiaria.com.uy/static/fonts/dialect/DialectGothicA-Regular.otf") format("opentype");
    }
    @font-face {
      font-family: "Dialect Gothic A";
      font-style: normal;
      font-weight: 700;
      src: url("https://ladiaria.com.uy/static/fonts/dialect/DialectGothicA-Bold.otf") format("opentype");
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: "Dialect Gothic A", sans-serif;
      background: #fff;
      color: #000;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      background-color: #F1F4F5;
    }

    header {
      background: #fff;
      border-bottom: 0.5px solid #ababab;
      padding: 0 48px;
      display: flex;
      justify-content: center;
    }

    .header__inner {
      width: 100%;
      max-width: 1280px;
      padding: 11px 0 10px;
      display: flex;
      justify-content: center;
    }

    main {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: space-between;
      padding-top: 112px;
    }

    .main__content {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 24px;
      text-align: center;
    }

    h1 {
      font-family: "Dialect Gothic A", sans-serif;
      font-weight: 700;
      font-size: 40px;
      letter-spacing: 0.01em;
      line-height: 1;
      color: #000;
    }

    .subtitle {
      font-family: "Dialect Gothic A", sans-serif;
      font-weight: 400;
      font-size: 24px;
      letter-spacing: 0.01em;
      color: #000;
    }

    .consultas {
      width: 100%;
      border-top: 0.5px solid #81898b;
      padding: 32px 16px;
      display: flex;
      justify-content: center;
      align-items: center;
    }

    .consultas p {
      font-family: "Dialect Gothic A", sans-serif;
      font-weight: 400;
      font-size: 16px;
      color: #44494b;
      text-align: center;
      line-height: 1.5;
    }

    .consultas strong {
      font-weight: 700;
    }

    .consultas a {
      color: #44494b;
      text-decoration: underline;
    }

    @media (max-width: 600px) {
      main { padding-top: 0; }
      .main__content {
        padding: 48px 20px 0;
        gap: 16px;
      }
      h1 { font-size: 28px; }
      .subtitle { font-size: 18px; }
      .consultas { padding: 24px 0; }
    }
  </style>
</head>
<body>
  <header>
    <div class="header__inner">
      <svg xmlns="http://www.w3.org/2000/svg" width="103" height="26" fill="none" viewBox="0 0 103 26"><path fill="#000" d="M97.334 25.784v-1.932c-.597 1.159-1.896 2.107-3.898 2.107h-1.3c-2.844 0-4.565-1.545-4.565-4.53V18.97c0-2.6 1.265-4.145 4.039-4.601 1.58-.246 3.371-.176 4.284-.421.913-.246 1.3-.808 1.3-1.862v-.948c0-1.334-.492-2.107-1.897-2.107-1.58 0-2.001 1.053-2.001 2.283v1.159h-5.444v-1.405c0-3.16 1.791-4.987 5.69-4.987h3.617c4.003 0 5.478 1.826 5.478 5.233v14.469zm-4.25-4.987c0 1.44.563 2.212 1.932 2.212 1.265 0 2.178-.808 2.178-2.458v-4.987c-.176.281-.422.492-.703.667-.456.281-1.159.457-1.826.703-1.159.456-1.58 1.018-1.58 2.388zM80.617 4.923V.076h5.62v4.847zm.035 1.334h5.55v19.526h-5.55zm-11.386.001h5.443v2.599c.737-1.862 1.967-2.634 3.371-2.634h1.37v5.127h-.492c-2.81 0-4.179.913-4.179 3.793v10.64h-5.513zm-7.021 19.526v-1.932c-.597 1.159-1.896 2.107-3.898 2.107h-1.3c-2.844 0-4.565-1.545-4.565-4.53V18.97c0-2.6 1.265-4.145 4.04-4.601 1.58-.246 3.37-.176 4.284-.421.913-.246 1.299-.808 1.299-1.862v-.948c0-1.334-.492-2.107-1.896-2.107-1.58 0-2.002 1.053-2.002 2.283v1.159h-5.444v-1.405c0-3.16 1.791-4.987 5.69-4.987h3.617c4.003 0 5.478 1.826 5.478 5.233v14.469zm-4.249-4.987c0 1.44.562 2.212 1.932 2.212 1.264 0 2.177-.808 2.177-2.458v-4.987a2.1 2.1 0 0 1-.702.667c-.457.281-1.16.457-1.827.703-1.159.456-1.58 1.018-1.58 2.388zM45.53 4.923V.076h5.62v4.847zm.035 1.334h5.55v19.526h-5.55zm-17.6 13.557v-7.586c0-4.25 1.756-6.146 4.917-6.146h1.334c2.037 0 3.336.843 4.039 2.107V.09h5.513v25.695h-5.513v-2.037c-.703 1.264-1.932 2.212-4.039 2.212h-1.334c-3.126 0-4.917-1.896-4.917-6.145m5.654-1.019c0 2.774.702 3.898 2.212 3.898 1.58 0 2.424-1.088 2.424-3.828v-5.689c0-2.774-.843-3.828-2.424-3.828-1.51 0-2.212 1.124-2.212 3.863zm-16.971 6.988v-1.932c-.597 1.159-1.897 2.107-3.898 2.107h-1.3c-2.844 0-4.565-1.545-4.565-4.53V18.97c0-2.6 1.264-4.145 4.038-4.601 1.58-.246 3.372-.176 4.285-.421.913-.246 1.3-.808 1.3-1.862v-.948c0-1.334-.492-2.107-1.897-2.107-1.58 0-2.002 1.053-2.002 2.283v1.159H7.166v-1.405c0-3.16 1.79-4.987 5.689-4.987h3.617c4.004 0 5.479 1.826 5.479 5.233v14.469zm-4.25-4.987c0 1.44.562 2.212 1.932 2.212 1.264 0 2.177-.808 2.177-2.458v-4.987c-.175.281-.421.492-.702.667-.457.281-1.159.457-1.826.703-1.16.456-1.58 1.018-1.58 2.388zM.121 0h5.514l-.121 25.784H0z"/></svg>
    </div>
  </header>
  <main>
    <div class="main__content">
      <h1>Ya volvemos</h1>
      <p class="subtitle">Estamos actualizando el sitio.</p>
    </div>
    <div class="consultas">
      <p>
        <strong>¿Tenés consultas?</strong><br>
        Visitá nuestro <a href="https://ayuda.ladiaria.com.uy/">centro de ayuda</a> o <a href="https://ayuda.ladiaria.com.uy/contacto/">contactanos</a>.
      </p>
    </div>
  </main>
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
