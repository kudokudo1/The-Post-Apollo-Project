// Visual motion only. The caller is the sole authority for operation state.
// Timed and measured progress are never replaced by an invented percentage.
function clamp(n, lo, hi) {
    return Math.max(lo, Math.min(hi, Number.isFinite(n) ? n : lo));
}
function smooth(n) {
    const x = clamp(n, 0, 1);
    return x*x*(3-2*x);
}
function frame(phase, mode, progress, seconds, finishFrom, reduced, variant) {
    const t = Math.max(0, Number.isFinite(seconds) ? seconds : 0);
    let p = 0;
    const running = phase === "running";
    const ki=variant==="ki-blast", tron=variant==="tron";
    const defeated=ki && phase==="failure";
    const exact = mode === "measured" || mode === "timed";
    if (running && exact) {
        p = clamp(progress, 0, 1);
    } else if (running && reduced) {
        // A stationary, explicitly indeterminate activity cue.
        p = ki ? .5 : .35;
    } else if (running && tron) {
        // Monotonic acceleration, then an asymptotic approach to the finish.
        p=.96*(1-Math.exp(-Math.pow(t/3.0,1.65)));
    } else if (running) {
        let base;
        if (t < .65) base = .055*smooth(t/.65);
        else if (t < 2.1) base = .055+.15*smooth((t-.65)/1.45);
        else if (t < 2.8) base = .205-.045*smooth((t-2.1)/.7);
        else if (t < 3.7) base = .16+.34*smooth((t-2.8)/.9);
        else if (t < 4.2) base = .50+.32*smooth((t-3.7)/.5);
        else base = .82+.115*(1-Math.exp(-(t-4.2)/6));
        const recoil = reduced ? 0 : (Math.sin(t*15)*.014+Math.sin(t*26)*.009
            +Math.sin(t*4.3)*.023)*(t<.65?.4:1);
        p = clamp(base+recoil, 0, .96);
        if (ki) p=.43+.55*p;
    } else if (phase === "success") {
        const start = clamp(finishFrom, 0, 1);
        p = reduced ? 1 : start+(1-start)*smooth(t/.42);
    } else if (phase === "ready") p = 1;
    else if (defeated) p = reduced ? 0 : clamp(finishFrom,0,1)*(1-smooth(t/.72));
    else if (phase === "failure") p = clamp(finishFrom, 0, 1);
    const strength = smooth((p-.38)/.60);
    const pulse = running && !reduced ? Math.sin(t*13)*.09+Math.sin(t*24)*.06 : 0;
    const impact = phase === "success" && !reduced
        ? smooth((t-.42)/.08)*(1-smooth((t-.50)/.34)) : 0;
    const clash=ki && (running || (phase==="success" && p<1)
        || defeated);
    // The enemy already carries a little red while fighting. Defeat makes
    // that heat spread continuously as the collision retreats to the origin.
    const redBase=.12+.06*(1-(defeated?clamp(finishFrom,0,1):p));
    const enemyHeat=ki && (clash || defeated)
        ? (defeated ? redBase+(1-redBase)*(reduced?1:smooth(t/.72)) : redBase) : 0;
    // The winning beam is the persistent failure indicator until reset.
    const enemyOpacity=clash ? 1 : 0;
    return {
        fraction: p, intensity: strength,
        clash:clash, enemyFraction:clash?1-p:0,
        enemyHeat:enemyHeat, enemyOpacity:enemyOpacity,
        defeat: defeated && !reduced ? (1-smooth(t/1.08)) : 0,
        power: 1+strength*.85+pulse*(1+strength)+impact*.65,
        brightness: 1+strength*1.15+impact*.7,
        dx: running && !reduced ? (Math.sin(t*39)+.4*Math.sin(t*19))*(.35+strength*.85) : 0,
        dy: running && !reduced ? Math.sin(t*31)*(.1+strength*.35) : 0,
        headVisible: running || (phase === "success" && !reduced && t<.84) || (defeated && !reduced && t<.72),
        impact: impact
    };
}
