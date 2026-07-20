from fastapi import FastAPI
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import HTMLResponse

SWAGGER_UI_THEME = """
<style>
  :root { color-scheme: light; --bg: #f6f8fb; --surface: #fff; --text: #18212f; }
  html[data-swagger-theme="dark"] {
    color-scheme: dark;
    --bg: #0b1120;
    --surface: #111827;
    --text: #e5edf7;
  }
  body, .swagger-ui { background: var(--bg); color: var(--text); }
  .swagger-ui .info .title, .swagger-ui .info p, .swagger-ui .opblock-tag,
  .swagger-ui .model-title, .swagger-ui .model, .swagger-ui label,
  .swagger-ui .response-col_status, .swagger-ui .response-col_description { color: var(--text); }
  .swagger-ui .scheme-container, .swagger-ui section.models,
  .swagger-ui .model-container, .swagger-ui .opblock .opblock-section-header {
    background: var(--surface); color: var(--text); border-color: #64748b;
  }
  html[data-swagger-theme="dark"] .swagger-ui .filter-container input[type="text"] {
    background: var(--surface);
    color: var(--text);
    border-color: #64748b;
  }
  html[data-swagger-theme="dark"]
    .swagger-ui .filter-container input[type="text"]::placeholder,
  html[data-swagger-theme="dark"] .swagger-ui .opblock-tag small {
    color: #94a3b8;
    opacity: 1;
  }
  html[data-swagger-theme="dark"] .swagger-ui svg {
    fill: var(--text);
  }
  html[data-swagger-theme="dark"] .swagger-ui .opblock .opblock-summary-path,
  html[data-swagger-theme="dark"]
    .swagger-ui .opblock .opblock-summary-path__deprecated,
  html[data-swagger-theme="dark"]
    .swagger-ui .opblock .opblock-summary-description {
    color: #e5edf7 !important;
  }
  html[data-swagger-theme="dark"] .swagger-ui section.models h4,
  html[data-swagger-theme="dark"] .swagger-ui .model-box-control,
  html[data-swagger-theme="dark"] .swagger-ui .model-box-control span {
    color: var(--text);
  }
  html[data-swagger-theme="dark"] .swagger-ui .model-box,
  html[data-swagger-theme="dark"] .swagger-ui .model-container {
    background: #0f172a;
  }
  html[data-swagger-theme="dark"] .swagger-ui .model-box-control,
  html[data-swagger-theme="dark"] .swagger-ui .json-schema-2020-12 button {
    padding: 0;
    border: 0;
    outline: 0;
    background: transparent !important;
    box-shadow: none;
  }
  html[data-swagger-theme="dark"] .swagger-ui .model-box-control:hover,
  html[data-swagger-theme="dark"] .swagger-ui .model-box-control:focus,
  html[data-swagger-theme="dark"] .swagger-ui .model-box-control:active,
  html[data-swagger-theme="dark"] .swagger-ui .json-schema-2020-12 button:hover,
  html[data-swagger-theme="dark"] .swagger-ui .json-schema-2020-12 button:focus,
  html[data-swagger-theme="dark"] .swagger-ui .json-schema-2020-12 button:active {
    background: transparent !important;
    box-shadow: none;
  }
  html[data-swagger-theme="dark"] .swagger-ui .model-title,
  html[data-swagger-theme="dark"] .swagger-ui .model .property,
  html[data-swagger-theme="dark"] .swagger-ui .model .property.primitive,
  html[data-swagger-theme="dark"] .swagger-ui .prop-name,
  html[data-swagger-theme="dark"] .swagger-ui .model .property-type,
  html[data-swagger-theme="dark"] .swagger-ui .model .description,
  html[data-swagger-theme="dark"] .swagger-ui .json-schema-2020-12 {
    color: #dbe4f0 !important;
  }
  html[data-swagger-theme="dark"] .swagger-ui .prop-type,
  html[data-swagger-theme="dark"] .swagger-ui .prop-format {
    color: #a5b4fc;
  }
  html[data-swagger-theme="dark"] .swagger-ui .model-toggle::after,
  html[data-swagger-theme="dark"] .swagger-ui .json-schema-2020-12 svg {
    color: #dbe4f0;
    fill: #dbe4f0;
  }
  #swagger-theme-toggle { position: fixed; z-index: 10000; top: 14px; right: 18px;
    height: 38px; padding: 0 14px; border: 1px solid #64748b; border-radius: 999px;
    background: var(--surface); color: var(--text); cursor: pointer; }
</style>
<script>
  (function () {
    function apply(theme) {
      document.documentElement.dataset.swaggerTheme = theme;
      const button = document.getElementById("swagger-theme-toggle");
      if (button) button.textContent = theme === "dark" ? "Светлая" : "Тёмная";
    }
    const saved = localStorage.getItem("swagger-theme");
    const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    apply(saved || preferred);
    window.addEventListener("load", function () {
      const button = document.createElement("button");
      button.id = "swagger-theme-toggle";
      button.type = "button";
      button.onclick = function () {
        const next = document.documentElement.dataset.swaggerTheme === "dark" ? "light" : "dark";
        localStorage.setItem("swagger-theme", next);
        apply(next);
      };
      document.body.appendChild(button);
      apply(document.documentElement.dataset.swaggerTheme);
    });
  })();
</script>
"""


def setup_docs_routes(app: FastAPI) -> None:
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html() -> HTMLResponse:
        if app.openapi_url is None:
            raise RuntimeError("OpenAPI URL is disabled")
        swagger_ui = get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url="/docs/oauth2-redirect",
            swagger_ui_parameters={
                "persistAuthorization": True,
                "displayRequestDuration": True,
                "filter": True,
                "defaultModelsExpandDepth": 1,
                "docExpansion": "none",
                "tryItOutEnabled": True,
            },
        )
        html = bytes(swagger_ui.body).decode("utf-8").replace(
            "</body>", f"{SWAGGER_UI_THEME}</body>"
        )
        return HTMLResponse(html)

    @app.get("/docs/oauth2-redirect", include_in_schema=False)
    async def swagger_ui_redirect() -> HTMLResponse:
        return get_swagger_ui_oauth2_redirect_html()
