mod common;
mod projections;

use pyo3::prelude::*;
use projections::{calculate_projections, ProjectionResult};


/// Módulo Python. El nombre DEBE coincidir con el `lib.name` en Cargo.toml.
#[pymodule]
fn fincore(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(calculate_projections, m)?)?;
    m.add_class::<ProjectionResult>()?;
    Ok(())
}