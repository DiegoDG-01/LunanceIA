# 🛠️ Troubleshooting — Lunance

Problemas conocidos del entorno de desarrollo y sus soluciones. Si el tuyo no está
aquí, abre un issue con el traceback completo y la salida de `uv pip list`.

---

## 🦀 `fincore` desaparece después de `uv sync`

### Síntoma

Tras cualquier `uv sync`, las proyecciones de inversión fallan:

```
ModuleNotFoundError: No module named 'fincore'
```

o, desde la API, el error de dominio:

```
The 'fincore' financial engine is not available.
```

### Causa

`fincore` es el motor de cálculo en Rust que vive en `fincore/`. Se compila con
maturin y se instala aparte, **a propósito no está en `uv.lock`**.

`uv sync` deja el entorno *exactamente* igual al lock, así que desinstala todo lo
que sobra — y `fincore` siempre sobra. No es un fallo de uv: es su comportamiento
por diseño.

### Solución: reinstalarlo

```bash
uv pip install ./fincore
```

Necesitas el toolchain de Rust ([rustup.rs](https://rustup.rs)). Tarda unos segundos
porque compila el crate en modo release.

Verifica:

```bash
python -c "import fincore; print(fincore.calculate_projections)"
```

### Cómo evitar que se borre

Pasa `--inexact`, que le dice a uv que no elimine paquetes ajenos al lock:

```bash
uv sync --all-groups --inexact
```

⚠️ Hay que pasar el flag **cada vez**: `--inexact` no tiene variable de entorno
equivalente, así que un `uv sync` a secas volverá a borrarlo. Si usas un alias de
shell, recuerda que `uv sync` desde el IDE o desde un hook no pasará por él.

> 💡 Si el proyecto ya estaba instalado y solo quieres actualizar dependencias sin
> tocar `fincore`, `uv sync --inexact` es la opción cómoda. Si acabas de clonar,
> instálalo con `uv pip install ./fincore` después del primer `uv sync`.
