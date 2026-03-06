/// Determina si un año es bisiesto.
/// Reemplaza a `shared/utils/date.py::get_year_day_basis()`
pub fn is_leap_year(year: i32) -> bool {
    (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0)
}

/// Retorna 366 si el año es bisiesto, 365 si no.
pub fn year_day_basis(year: i32) -> u32 {
    if is_leap_year(year) { 366 } else { 365 }
}

/// Avanza una fecha (year, month, day) en 1 día.
/// Maneja cambios de mes y año correctamente.
pub fn advance_date(year: i32, month: u32, day: u32) -> (i32, u32, u32) {
    let days_in_month = match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 => if is_leap_year(year) { 29 } else { 28 },
        _ => unreachable!(),
    };

    if day < days_in_month {
        (year, month, day + 1)
    } else if month < 12 {
        (year, month + 1, 1)
    } else {
        (year + 1, 1, 1)
    }
}