# Design notes (working log, netlist-level results before schematic capture)

Supply: single Vunregulated = 5 V source, single ground. Regulator output VREF = VDD = 3.0 V for DAC + op-amp.

## Results so far (27 °C unless stated)
| Item | Result |
|---|---|
| VREF (= VDD) | 3.0037 V, TC 7.3 ppm/°C (0–80 °C) |
| IPTAT / ICONST | 9.7 µA / 27.6 µA |
| VX (bandgap voltage) | 2.002 V |
| LDO load regulation | 2.5 mV for 1 → 51 mA; 50 mA step: −126 mV / +100 mV, recovers < 20 µs |
| Op-amp open-loop gain / PM / UGB | 114.7 dB / 83.8° / 13.2 MHz (VBN/VCN ideal, unloaded) |
| Op-amp buffer range | 0 V to 1.48 V while sourcing 50 mA (15.75 Ω load) |
| DAC INL / DNL (system, systematic only) | ±0.016 LSB, monotonic |
| Output TC, code 011111 / 111111 | 10.9 / 9.7 ppm/°C |

## Design iterations that mattered
1. Banba-type core has a degenerate low-current equilibrium (NPNs off, R2 = R4 carry equal current). Start-up must inject into node A, pull down PG and VCPI, and turn off only when node A reaches ~VBE (sensed by M2's gate).
2. PMOS cascode bias VCPI generated for one current density -> all PMOS mirrors in the regulator sized to the same density (W = 66 µm at 27 µA).
3. Op-amp headroom: VCN raised (M17 W = 5 µm) and RB = 60 kΩ so M30/M37/M44 and M34/M41 stay saturated.
4. Output TC was 169 ppm/°C: (a) VBN diode VDS ≠ copies' VDS -> cascoded VBN reference (M14b); (b) BSIM3 width-dependent Vt made 19.8 µm vs 30 µm mirrors non-ratiometric -> all mirrored NMOS built from identical 5 µm unit devices with multiplier m; (c) NPN start-up detector saturated and loaded node A -> replaced by NMOS M2 (gate = node A). Result 10.9 / 9.7 ppm/°C.
