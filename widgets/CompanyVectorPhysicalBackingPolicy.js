.pragma library

// COMPANY M30u // candidate-only physical buffer geometry.
// M30t headless Mesa/Wayland proved that a 1493x788 Company map canvas
// rendered from a 1493x788 Qt buffer sheared ordinary Qt rectangles in
// the compositor. A 1494x788 physical Qt buffer cropped to the SAME
// 1493x788 visible canvas had 0px vertical/horizontal drift.
//
// Important: the 8-byte/4-byte row-pitch model is an engineering
// HYPOTHESIS consistent with the pixel evidence, NOT an attested dmabuf
// format, native executable trust assertion or production authorization.
// No caller is allowed to reinterpret this calculation as scene, input,
// focus, clip, size, installation or user-location permission.

var FORMAT = "post-apollo.company.vector-physical-backing.m30u.v1";
var PROOF = "SwayPX-M30t-CI-20261108";
var MAX_WIDTH = 4096;
var MAX_HEIGHT = 2160;

function _integer(v) {
    return typeof v === "number" && isFinite(v) &&
        Math.floor(v) === v;
}

function _refused(reason) {
    return {
        status: "REFUSED",
        reason: reason,
        candidateOnly: true,
        productionAuthority: false,
        schema: FORMAT
    };
}

// Explicit 4-bytes-per-pixel, 8-byte-alignment *candidate* for the
// CI-observed software renderer only. Returning an ordinary calculation
// must NEVER approve a native actor or imply the format is correct for
// another machine/output. The compositor still owns its own checked
// crop, size and trusted-host policy.
function candidate(visibleWidth, visibleHeight, bytesPerPixel, rowAlignmentBytes) {
    if (!_integer(visibleWidth) || !_integer(visibleHeight) ||
            visibleWidth <= 0 || visibleHeight <= 0 ||
            visibleWidth > MAX_WIDTH || visibleHeight > MAX_HEIGHT)
        return _refused("INVALID_OR_UNSUPPORTED_VIEWPORT");

    // No silent assumption about the buffer's actual format/stride.
    // The M30t parity evidence only exercises this model.
    if (bytesPerPixel !== 4 || rowAlignmentBytes !== 8)
        return _refused("UNVERIFIED_BUFFER_FORMAT_OR_ROW_ALIGNMENT");

    var logicalStride = visibleWidth * bytesPerPixel;
    var remainder = logicalStride % rowAlignmentBytes;
    var paddingBytes = remainder === 0 ? 0 : rowAlignmentBytes - remainder;
    if (paddingBytes % bytesPerPixel !== 0)
        return _refused("NONINTEGRAL_PIXEL_PADDING");

    var paddingColumns = paddingBytes / bytesPerPixel;
    var backingWidth = visibleWidth + paddingColumns;
    if (backingWidth > MAX_WIDTH)
        return _refused("BACKING_EXCEEDS_MAX_WIDTH");

    var backingStride = backingWidth * bytesPerPixel;
    if (backingStride % rowAlignmentBytes !== 0 ||
            backingStride <= 0 || backingStride > MAX_WIDTH * 4)
        return _refused("UNALIGNED_BACKING_ROW");

    var directlyTested = visibleWidth === 1493 &&
        visibleHeight === 788 && backingWidth === 1494;
    return {
        schema: FORMAT,
        status: "CANDIDATE_ONLY",
        candidateOnly: true,
        productionAuthority: false,
        sourceProof: PROOF,
        evidenceLevel: directlyTested
            ? "EXACT_CI_OBSERVATION"
            : "ARITHMETIC_ONLY_UNVERIFIED_FOR_REAL_RENDERER",
        logicalWidth: visibleWidth,
        logicalHeight: visibleHeight,
        physicalWidth: backingWidth,
        physicalHeight: visibleHeight,
        rightCropColumns: paddingColumns,
        assumedBytesPerPixel: bytesPerPixel,
        assumedRowAlignmentBytes: rowAlignmentBytes,
        calculatedStrideBytes: backingStride,
        visibleRect: {
            x: 0,
            y: 0,
            width: visibleWidth,
            height: visibleHeight
        }
    };
}
