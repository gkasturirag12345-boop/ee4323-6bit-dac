import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
OUT="../../Simulation_Results/block_diagram.png"
fig,ax=plt.subplots(figsize=(12,6.8)); ax.set_xlim(0,122); ax.set_ylim(-6,62); ax.axis('off')
def box(x,y,w,h,title,lines,fc):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.4",fc=fc,ec="#333",lw=1.2))
    ax.text(x+w/2,y+h-2.2,title,ha='center',va='top',fontsize=10,weight='bold')
    for k,l in enumerate(lines): ax.text(x+w/2,y+h-6.2-k*2.6,l,ha='center',va='top',fontsize=6.6)
def arrow(p,q,c,lw=1.6,txt=None,tp=None,ls='-'):
    ax.add_patch(FancyArrowPatch(p,q,arrowstyle='-|>',mutation_scale=12,color=c,lw=lw,linestyle=ls))
    if txt: ax.text(*(tp or ((p[0]+q[0])/2,(p[1]+q[1])/2+1)),txt,fontsize=7.8,color=c,ha='center',weight='bold')
# blocks
box(1,40,19,12,"Vunregulated",["single 5 V source","(one ground: GND / analog GND)"],"#eeeeee")
box(24,26,26,30,"Voltage Regulator",["(handout p.3; PMOS bodies to Vunreg)","M1-M7 + R1: I_CONST,Gm (start-up)","PTAT: Ma (A=8)+R3 / Mb (A=1): 10 uA","CTAT: R2, R4; Mc + Cc1 loop",
    "ICONST = IPTAT + ICTAT (= IREF)","Bias: VBP, VCP, VCN, VBN","VX = ICONST x R5 = 2.80 V","LDO: M23/M25 + M24/M28, pass M29","VREF = VX(1+R7/R6) = 3.62 V"],"#dbe9f7")
box(58,26,24,22,"DAC Core",["(handout p.2) M50-M53 -> VBP2, VCP2","unary D1-D3: 3 x 16 I_LSB","W-2W ladder B3-B6 (8,4,2,1)","M54-M59 + 16 x M58: terminator","PMOS switch pairs, RDAC = 5.778 k"],"#e3f2df")
box(90,30,24,18,"OpAmp (buffer)",["(handout p.4) M46-M49 -> VBP1, VCP1","PMOS pair M32 (+) / M33 (-)","folded cascode, M42 + CA","M45 follower + ROUT","unity gain, 50 ohm / 50 mA"],"#fbe7d3")
box(58,0,24,15,"Logic stimuli (counter)",["clk_D1..clk_D3 (thermometer)","clk_B3..clk_B6 (binary)","+ clk_bar_* complements","0-3.62 V, tr = tf = 5 ns"],"#f3e6f7")
ax.text(119,40.5,"VOUT",fontsize=11,weight='bold',ha='center')
# power
arrow((18,46),(24,46),'#b00000',2.2,'Vunreg','top' and None)
ax.plot([50,102],[53,53],color='#b00000',lw=2.2); ax.text(56,54.3,'VREG as VDD = VREF (3.62 V)',fontsize=7.8,color='#b00000',weight='bold')
arrow((70,53),(70,48.4),'#b00000',2.2); arrow((102,53),(102,48.4),'#b00000',2.2)
# bias
arrow((50,36),(58,36),'#1f5fbf',1.6,'VBN, VCN',(54,37.5))
ax.plot([50,54,54,96,96],[31,31,23,23,23],color='#1f5fbf',lw=1.6,ls='--'); arrow((96,23),(96,29.6),'#1f5fbf',1.6); ax.text(88,21.2,'VBN, VCN to op-amp',fontsize=7.8,color='#1f5fbf',ha='center',weight='bold')
# clocks
for k,x in enumerate([62,66,70,74,78]): arrow((x,15.4),(x,25.6),'#7b3fa0',1.2)
ax.text(84,10,'14 lines:\nclk / clk_bar',fontsize=7.8,color='#7b3fa0',weight='bold')
# signal
arrow((82,40),(90,40),'#137a13',2.0,'IOUT',(86,41.5)); arrow((114.4,39),(117,39),'#137a13',2.0)
ax.plot([108,108],[39,39],color='#137a13')
ax.text(61,-5.5,"Power (red), bias distribution (blue), logic/clock distribution (purple), signal path (green). "
        "IREF = ICONST (internal to the regulator); an ideal VCVS (gain 1e6) on the same IOUT node gives VOUT_IDEAL.",fontsize=7.5,ha='center')
fig.savefig(OUT,dpi=200,bbox_inches='tight'); print(OUT)
