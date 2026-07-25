# Política de Seguridad — Lunance IA

Lunance IA maneja datos financieros personales. Tomamos en serio cualquier reporte de vulnerabilidad y agradecemos la divulgación responsable.

## 🚨 Cómo reportar una vulnerabilidad

**No abras un issue público, un Pull Request ni un mensaje en Discussions para reportar un problema de seguridad.** Hacerlo expone a los usuarios antes de que exista una corrección.

Usa uno de estos canales privados:

1. **GitHub Security Advisories** (preferido): pestaña **Security → Report a vulnerability** del repositorio. El reporte queda visible solo para los mantenedores.
2. **Correo**: contacto@diegodg.com.mx

Si necesitas cifrar el reporte, indícalo en el primer mensaje y te enviaremos una clave pública.

## 📋 Qué incluir en el reporte

Cuanta más información des, más rápido podremos reproducir y corregir:

- Tipo de vulnerabilidad (p. ej. IDOR, inyección SQL, escalada de privilegios, exposición de datos, fallo de autenticación).
- Rutas o endpoints afectados, y la versión o commit donde lo observaste.
- Pasos detallados para reproducirlo, incluyendo peticiones HTTP de ejemplo.
- Prueba de concepto, si la tienes.
- Impacto que estimas: qué datos o acciones quedan expuestos y para qué tipo de atacante.
- Si el hallazgo ya es público o lo has compartido con terceros.

## ⏱️ Qué puedes esperar

| Etapa | Plazo objetivo |
|---|---|
| Acuse de recibo | 72 horas |
| Evaluación inicial y clasificación de severidad | 7 días naturales |
| Actualización de estado | Cada 14 días mientras el caso siga abierto |
| Corrección de vulnerabilidades críticas o altas | 30 días desde la confirmación |
| Corrección de severidad media o baja | Siguiente ciclo de release planificado |

Estos plazos son objetivos de buena fe para un proyecto mantenido por una sola persona, no un compromiso contractual.

## 🤝 Divulgación coordinada

Te pedimos que:

- Nos des un plazo razonable para corregir antes de hacer público el hallazgo. Nuestro estándar es **90 días** desde el acuse de recibo, o el día en que se publique la corrección si es antes.
- No accedas, modifiques ni extraigas datos de otras personas. Si durante la prueba obtienes acceso a datos ajenos, detente y descríbelo en el reporte.
- No degrades el servicio: sin pruebas de denegación de servicio, sin fuerza bruta masiva, sin spam a usuarios reales.
- No uses ingeniería social contra el mantenedor ni contra terceros.

Por nuestra parte, nos comprometemos a responder, a mantenerte informado del avance y a **acreditarte públicamente** en el aviso de seguridad, salvo que prefieras permanecer anónimo.

Este proyecto **no ofrece recompensas económicas** (bug bounty) por reportes de seguridad.

## ✅ Alcance

**Dentro del alcance:**

- Código de la API en `src/`, incluidos endpoints, autenticación, autorización y lógica de negocio con impacto financiero.
- Migraciones de base de datos en `alembic/` y consultas en `sql/`.
- Configuración de despliegue del repositorio: `Dockerfile`, `Dockerfile.mcp`, `docker-compose.yml`, workflows de `.github/`.
- Exposición de secretos o credenciales en el historial del repositorio.
- El servidor MCP incluido en el proyecto.

**Fuera del alcance:**

- Vulnerabilidades en dependencias de terceros que ya tengan un aviso público: repórtalas al proyecto correspondiente. Si aquí falta actualizar la dependencia, abre un issue normal.
- Servicios de terceros que integramos (Auth0, Google Gemini, OpenAI, Redis gestionado, proveedores de hosting): repórtalos a su programa de seguridad.
- Resultados de escáneres automáticos sin impacto demostrable.
- Ausencia de cabeceras de seguridad o de buenas prácticas sin un vector de ataque concreto.
- Ataques que requieran acceso físico al dispositivo, malware previo en la máquina de la víctima, o una cuenta ya comprometida.
- Despliegues de terceros que ejecuten forks del proyecto: repórtalos a quien los opera.

## 📦 Versiones con soporte

Solo la última versión publicada en la rama `master` recibe parches de seguridad. Actualiza a la última release antes de reportar un fallo que puede estar ya corregido.

## 🔐 Buenas prácticas para quien despliegue el proyecto

Si ejecutas Lunance IA por tu cuenta:

- Nunca subas tu `.env` al control de versiones; parte de `.env.example`.
- Genera tus propias claves y secretos: no reutilices los valores de ejemplo de la documentación.
- Ejecuta con `ENVIRONMENT=PROD` en producción — `DEV` habilita CORS abierto y trazas detalladas en los errores.
- Sirve siempre la API tras TLS.
- Restringe el acceso de red a MySQL y Redis; no los expongas a Internet.
- Mantén las dependencias al día (`uv sync`) y revisa los avisos de Dependabot.

---

Gracias por ayudar a mantener seguros los datos financieros de los usuarios de Lunance IA.
