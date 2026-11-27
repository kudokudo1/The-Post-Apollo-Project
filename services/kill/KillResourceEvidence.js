// Identity-correlated read-only capability envelope, not a permission grant.
function decode(output,requestKey) {
    if(typeof output!=="string"||output.length>32768||!requestKey) return null;
    try {
        var reply=JSON.parse(output);
        if(!reply||reply.schema!=="post-apollo-kill-capability-k8c-v1"||reply.state!=="observed"
            ||!reply.target||JSON.stringify([reply.target.pid,reply.target.startTicks,reply.target.comm])!==requestKey
            ||!reply.limits||reply.limits.no_syscall_mutations!==true
            ||reply.limits.host_observation_is_not_authorization!==true) return null;
        var resources=reply.resources;
        if(!resources||!resources.gpu||!resources.network) return null;
        for(var key of ["gpu","network"]) {
            var row=resources[key];
            if(row.actuation!=="not_verified"||row.permission_to_change!=="not_verified"||!row.observation) return null;
        }
        var gpu=resources.gpu.observation,net=resources.network.observation;
        var states=["observed","not_observed","permission_denied","missing","unavailable","oversize"];
        if(states.indexOf(gpu.drm_fdinfo)<0||states.indexOf(net.network_namespace)<0
            ||gpu.per_process_gpu_control!=="not_verified"
            ||net.per_process_bandwidth_control!=="not_verified"
            ||net.per_process_attribution!=="not_verified") return null;
        return {key:requestKey,gpu:gpu.drm_fdinfo,network:net.network_namespace};
    } catch(error) { return null; }
}
