.pragma library

// COMPANY M30x // CI-only imported-buffer evidence reconciliation.
// M30t proved a 1494x788 Qt source cropped to a 1493x788 Company map
// has straight output pixels in one isolated Wayland test.
// M30v measured an RGBA CPU QImage pitch of 5976 bytes.
// M30w separately observed the imported wlroots SHM RGB565 buffer at
// 1494x788, 2988 bytes/row. These are NOT the same allocation.
// This helper compares caller-supplied metadata against that recorded
// CI profile. It does not authenticate the caller, host, surface or GPU,
// and NEVER authorizes production rendering, focus, input or clipping.

var SCHEMA = "post-apollo.company.vector-native-buffer-reconciliation.m30x.v1";
var PROOF = "SwayPX-M30w-CI-42513247422";
var FOURCC_RGB565 = "0x36314752";

function refused(reason) {
    return {
        schema: SCHEMA,
        status: "REFUSED",
        reason: reason,
        candidateOnly: true,
        productionAuthority: false,
        selectedNativeActorAuthorized: false,
        sceneAuthority: false,
        inputAuthority: false
    };
}

// `imported` is a normalized, untrusted copy of the M30w CI observer's
// SHM fields, NOT a kernel-backed attestation or an admission token.
// Do not derive new alignment rules or infer the original 1493px pitch.
// A matching record is a match to ONE known CI reference, nothing more.
function compare(visibleWidth, visibleHeight, imported) {
    if (visibleWidth !== 1493 || visibleHeight !== 788)
        return refused("VISIBLE_GEOMETRY_NOT_TESTED");
    if (!imported || typeof imported !== "object" || Array.isArray(imported))
        return refused("MISSING_OR_INVALID_NATIVE_METADATA");

    if (imported.allocationKind !== "SHM" ||
            imported.fourcc !== FOURCC_RGB565)
        return refused("UNREVIEWED_NATIVE_PIXEL_FORMAT");
    if (imported.physicalWidth !== 1494 ||
            imported.physicalHeight !== 788 ||
            imported.planeCount !== 1)
        return refused("NATIVE_GEOMETRY_OR_PLANES_MISMATCH");
    if (imported.strideBytes !== 2988)
        return refused("NATIVE_STRIDE_MISMATCH");
    if (imported.scale !== 1 || imported.transform !== 0 ||
            imported.modifier !== null)
        return refused("NATIVE_SURFACE_PROFILE_UNREVIEWED");

    return {
        schema: SCHEMA,
        status: "MATCHES_RECORDED_CI_PROFILE_ONLY",
        candidateOnly: true,
        productionAuthority: false,
        selectedNativeActorAuthorized: false,
        sceneAuthority: false,
        inputAuthority: false,
        metadataTrust: "CALLER_SUPPLIED_NOT_AUTHENTICATED",
        sourceProof: PROOF,
        evidenceScope: "ONE_HEADLESS_MESA_WAYLAND_TEST",
        visibleWidth: 1493,
        visibleHeight: 788,
        nativePhysicalWidth: 1494,
        nativePhysicalHeight: 788,
        rightCropColumns: 1,
        nativeAllocationKind: "SHM",
        nativeFourcc: FOURCC_RGB565,
        nativePixelFormat: "RGB565",
        nativeBytesPerPixel: 2,
        nativeStrideBytes: 2988,
        qtCpuReadbackFormatReference: "RGBA8888",
        qtCpuReadbackStrideBytesReference: 5976,
        cpuReadbackIsNativeAllocation: false,
        m30uFourByteEightByteModelIsNativeEvidence: false,
        originalUnpaddedNativeStrideBytes: null,
        actualFedoraBufferProfileVerified: false,
        universalStrideAlignmentVerified: false
    };
}
