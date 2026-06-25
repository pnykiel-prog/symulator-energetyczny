"""Testy konwersji jednostek (rdzeń łańcucha jednostkowego)."""

import math

from koferymentacja.core import units


def test_mg_kg_roundtrip():
    assert units.mg_to_kg(1.0) == 1000.0
    assert units.kg_to_mg(1000.0) == 1.0


def test_ch4_volume_skracanie_tysiecy():
    # 100 Mg VS * 350 NL/kg VS = 35 000 000 Nm3 (mnożniki 1000 się skracają)
    assert units.ch4_volume_from_vs_load(100.0, 350.0) == 35000.0


def test_energy_from_ch4():
    # 1000 Nm3 CH4 * 9,97 kWh/Nm3 = 9970 kWh
    assert math.isclose(units.energy_from_ch4_volume(1000.0, 9.97), 9970.0)


def test_gas_mass_from_volume():
    # 1000 Nm3 * 1,22 kg/Nm3 = 1220 kg = 1,22 Mg
    assert math.isclose(units.gas_mass_mg_from_volume(1000.0, 1.22), 1.22)
