mod common;
mod projections;

use pyo3::prelude::*;
use pyo3::create_exception;
use pyo3::exceptions::PyException;
use projections::{calculate_projections, ProjectionResult};

create_exception!(fincore, FinCoreError, PyException);
create_exception!(fincore, FCInvalidDecimalError, FinCoreError);
create_exception!(fincore, FCInvalidDateError, FinCoreError);

/// Módulo Python. El nombre DEBE coincidir con el `lib.name` en Cargo.toml.
#[pymodule]
fn fincore(m: &Bound<'_, PyModule>) -> PyResult<()> {

    m.add("FinCoreError", m.py().get_type::<FinCoreError>())?;
    m.add("FCInvalidDecimalError", m.py().get_type::<FCInvalidDecimalError>())?;
    m.add("FCInvalidDateError", m.py().get_type::<FCInvalidDateError>())?;

    m.add_function(wrap_pyfunction!(calculate_projections, m)?)?;
    m.add_class::<ProjectionResult>()?;
    Ok(())
}