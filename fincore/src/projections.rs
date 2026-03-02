use pyo3::prelude::*;
use rust_decimal::Decimal;
use rust_decimal::MathematicalOps;
use std::str::FromStr;

use crate::common::date::{advance_date, year_day_basis};
use crate::{FinCoreError, FCInvalidDecimalError};


#[pyclass(frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct FinCoreDetails {
    #[pyo3(get)]
    pub field: String,      // "current_balance", "annual_rate", "base_principal"
    #[pyo3(get)]
    pub message: String,    // "Invalid decimal: unknown character"
    #[pyo3(get)]
    pub error_type: String, // "INVALID_TYPE"
}

/// Resultado de la proyección de un día.
/// Se expone como clase Python para que el handler pueda leer los campos.
#[pyclass(frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct ProjectionResult {
    #[pyo3(get)]  // Permite acceso desde Python: result.year
    year: i32,
    #[pyo3(get)]
    month: u32,
    #[pyo3(get)]
    day: u32,
    #[pyo3(get)]
    principal_amount: String,  // String porque Python lo convertirá a Decimal
    #[pyo3(get)]
    yield_amount: String,
    #[pyo3(get)]
    projected_balance: String,
}

/// Calcula las proyecciones de inversión día a día.
///
/// # Argumentos (todos como tipos simples para facilitar el marshalling Python <-> Rust)
///
/// * `current_balance` - Balance actual de la cuenta (ej: "10000.00")
/// * `annual_rate` - Tasa de interés anual como porcentaje (ej: "12.5" para 12.5%)
/// * `interest_type` - "COMPOUND" o "SIMPLE"
/// * `days` - Número de días a proyectar (1-3650)
/// * `start_year`, `start_month`, `start_day` - Fecha de inicio (hoy)
/// * `base_principal` - Principal fijo para interés simple (None usa current_balance)
///
/// # Retorna
///
/// Vec<ProjectionResult> con la proyección de cada día
#[pyfunction]
pub fn calculate_projections(
    current_balance: &str,
    annual_rate: &str,
    interest_type: &str,
    days: u32,
    start_year: i32,
    start_month: u32,
    start_day: u32,
    base_principal: Option<&str>,
) -> PyResult<Vec<ProjectionResult>> {
    let mut balance = Decimal::from_str(current_balance)
        .map_err(|e| {
            let detail = FinCoreDetails {
                field: "current_balance".to_string(),
                message: format!("{}", e),
                error_type: "INVALID_TYPE".to_string(),
            };
            FCInvalidDecimalError::new_err((detail.message.clone(), detail.field.clone(), detail.error_type.clone()))
        })?;

    let rate = Decimal::from_str(annual_rate)
        .map_err(|e| {
            let detail = FinCoreDetails {
                field: "annual_rate".to_string(),
                message: format!("Invalid annual rate: {}", e),
                error_type: "INVALID_TYPE".to_string(),
            };
            FCInvalidDecimalError::new_err((detail.message.clone(), detail.field.clone(), detail.error_type.clone()))
        })?;

    let is_compound = interest_type == "COMPOUND";

    let original_principal = if !is_compound {
        match base_principal {
            Some(bp) => Decimal::from_str(bp)
                .map_err(|e| {
                    let detail = FinCoreDetails {
                        field: "base_principal".to_string(),
                        message: format!("Invalid base_principal: {}", e),
                        error_type: "INVALID_TYPE".to_string(),
                    };
                    FCInvalidDecimalError::new_err((detail.message.clone(), detail.field.clone(), detail.error_type.clone()))
                })?,
            None => balance,
        }
    } else {
        balance  // No se usa en compound, pero necesitamos un valor
    };

    let hundred = Decimal::from(100);
    let one = Decimal::from(1);

    let mut results = Vec::with_capacity(days as usize);
    let mut current_year = start_year;
    let mut current_month = start_month;
    let mut current_day = start_day;

    for _ in 0..days {
        // Avanzar un día
        let (y, m, d) = advance_date(current_year, current_month, current_day);
        current_year = y;
        current_month = m;
        current_day = d;

        let basis = Decimal::from(year_day_basis(current_year));

        let (principal, daily_yield) = if is_compound {
            // Interés compuesto:
            // daily_rate = (1 + annual_rate/100) ^ (1/year_basis) - 1
            // yield = balance * daily_rate
            let base = one + rate / hundred;
            let exponent = one / basis;
            let daily_rate = base.powd(exponent) - one;
            let yield_amount = (balance * daily_rate).round_dp(2);
            (balance, yield_amount)
        } else {
            // Interés simple:
            // daily_rate = annual_rate / 100 / year_basis
            // yield = original_principal * daily_rate
            let daily_rate = rate / hundred / basis;
            let yield_amount = (original_principal * daily_rate).round_dp(2);
            (original_principal, yield_amount)
        };

        balance += daily_yield;

        results.push(ProjectionResult {
            year: current_year,
            month: current_month,
            day: current_day,
            principal_amount: principal.to_string(),
            yield_amount: daily_yield.to_string(),
            projected_balance: balance.to_string(),
        });
    }

    Ok(results)
}