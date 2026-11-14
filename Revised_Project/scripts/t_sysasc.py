import run_asc, sys_asc, sys_tran, dac_static, stim, sim
log,d,g=run_asc.run(sys_asc.LT/'DAC_System.asc')
print(sim.errors(log)[:3]); print([v.name for v in d.variables][:12])
_,sched=stim.pwl_sources(300e-6,20e-6)
vo=sys_tran.sample(g,sched,20e-6); r=dac_static.lin(vo)
print('VOUT0 %.4f mV FS %.3f mV LSB %.4f | DNL %.4f/%.4f INL %.4f/%.4f gain %.3f mono %s'%(vo[0]*1e3,vo[-1]*1e3,r['lsb']*1e3,r['dnl'].max(),r['dnl'].min(),r['inl'].max(),r['inl'].min(),r['gain_err_lsb'],r['mono']))
