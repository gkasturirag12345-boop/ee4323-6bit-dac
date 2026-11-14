EE4323 6-bit segmented current-steering DAC - submission

LTspice schematics (open from this folder; the model files and .asy symbols must stay beside them):
  01_Characterisation.asc       NMOS / PMOS / NPN characterisation (Characterisation.pdf)
  02_VREF_Regulator.asc         buffered current-mode voltage reference / LDO (6-bit DAC.pdf p.3)
  03_Folded_Cascode_OpAmp.asc   ground-compatible folded-cascode op-amp (p.4)
  04_Complete_6Bit_DAC.asc      complete system (p.1-4) with 50 ohm load, ideal VCVS reference buffer, 14 logic sources
Support files: EE4323_cmos.mos, EE4323_bjt.lib, nmos_NWS.asy, pmos_PHL.asy, npn_npn.asy, R_ndiff.asy
Each schematic holds several analysis directives; exactly one is active, the others are comments (";").

Report/                 EE4323_DAC_Report.docx (+ .pdf)
Simulation_Results/     logs, CSV data, figures and summary.json per block; device_sizing_table.csv
Supporting_Documents/   scripts that generate, verify (LTspice netlist vs intended netlist) and simulate the
                        schematics, and the course model files
