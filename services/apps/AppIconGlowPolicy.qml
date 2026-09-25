import QtQuick

// Team 8 — APPS Core icon-glow presentation policy.
//
// Pure APPS presentation state. A palette is injected so this component does
// not own global theme semantics. It performs no image capture/readback itself;
// callers supply RGBA pixel data and may cache the resulting presentation color.
QtObject {
    id: policy

    property var colors: null
    property var cache: ({})

    function palette(name) {
        if (!colors)
            return null;

        const value = colors[name];
        return value === undefined ? null : value;
    }

    function cached(source) {
        const key = source ? source.toString() : "";

        if (!key || cache[key] === undefined)
            return null;

        return cache[key];
    }

    function remember(source, color, forceOverwrite) {
        const key = source ? source.toString() : "";

        if (!key)
            return false;

        if (!forceOverwrite && cache[key] !== undefined)
            return false;

        // Preserve donor QML binding semantics: reassign the object rather than
        // mutating one key in place.
        const next = Object.assign({}, cache);
        next[key] = color;
        cache = next;
        return true;
    }

    function classify(pixelData) {
        if (!pixelData || pixelData.length < 4)
            return palette("orange");

        let redAccent = 0;
        let orangeAccent = 0;
        let magentaAccent = 0;
        let cyanAccent = 0;
        let greenAccent = 0;

        let totalVisibleWeight = 0;
        let totalAccentWeight = 0;

        let lightNeutralWeight = 0;
        let darkNeutralWeight = 0;
        let midNeutralWeight = 0;

        for (let i = 0; i < pixelData.length; i += 4) {
            const alpha = pixelData[i + 3] / 255.0;

            if (alpha < 0.12)
                continue;

            const r = pixelData[i] / 255.0;
            const g = pixelData[i + 1] / 255.0;
            const b = pixelData[i + 2] / 255.0;

            const maxValue = Math.max(r, g, b);
            const minValue = Math.min(r, g, b);
            const delta = maxValue - minValue;

            const saturation = maxValue <= 0.0001
                ? 0.0
                : delta / maxValue;

            totalVisibleWeight += alpha;

            // Preserve donor ordering: classify saturated dark colors by hue
            // before treating them as neutral black.
            if (saturation >= 0.18 && delta >= 0.035) {
                let hue = 0.0;

                if (maxValue === r) {
                    hue = 60.0 * (((g - b) / delta) % 6.0);
                } else if (maxValue === g) {
                    hue = 60.0 * (((b - r) / delta) + 2.0);
                } else {
                    hue = 60.0 * (((r - g) / delta) + 4.0);
                }

                if (hue < 0.0)
                    hue += 360.0;

                const accentWeight =
                    alpha
                    * (0.55 + saturation * 1.45)
                    * (0.65 + maxValue * 0.35);

                totalAccentWeight += accentWeight;

                if (hue < 15.0 || hue >= 345.0) {
                    redAccent += accentWeight;
                } else if (hue < 75.0) {
                    orangeAccent += accentWeight;
                } else if (hue < 170.0) {
                    greenAccent += accentWeight;
                } else if (hue < 245.0) {
                    cyanAccent += accentWeight;
                } else {
                    magentaAccent += accentWeight;
                }

                continue;
            }

            if (maxValue > 0.72) {
                lightNeutralWeight += alpha;
            } else if (maxValue < 0.26) {
                darkNeutralWeight += alpha;
            } else {
                midNeutralWeight += alpha;
            }
        }

        const accentPresence =
            totalVisibleWeight > 0.0
            ? totalAccentWeight / totalVisibleWeight
            : 0.0;

        if (accentPresence >= 0.04) {
            const bestAccent = Math.max(
                redAccent,
                orangeAccent,
                magentaAccent,
                cyanAccent,
                greenAccent
            );

            if (bestAccent === redAccent)
                return palette("red");

            if (bestAccent === greenAccent)
                return palette("omnitrix");

            if (bestAccent === cyanAccent)
                return palette("cyan");

            if (bestAccent === magentaAccent)
                return palette("magenta");

            return palette("orange");
        }

        if (lightNeutralWeight > darkNeutralWeight
                && lightNeutralWeight > midNeutralWeight) {
            return palette("white");
        }

        return palette("magenta");
    }
}
