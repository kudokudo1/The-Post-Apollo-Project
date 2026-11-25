import QtQuick
import "../../services/git/GitMapViewportPolicy.js" as Policy

// Shared by GitW's two map hosts. No deletion authority.
Item {
    id: root
    visible: false
    property bool v2Mode: false
    property string v2Base: ""
    property var leases: []
    readonly property int leaseCount: leases.length
    readonly property int heldCount: leases.filter(l=>l.held).length
    Component { id: factory; GitMapGenerationLease {} }
    function acquire(g) {
        if (!g || !Policy.manifest(g.manifest) || g.manifest.shallow
                || g.repoId!==g.manifest.repoId || typeof g.key!=="string"
                || !/^[0-9a-f]{64}$/.test(g.key) || typeof g.directory!=="string"
                || !g.directory.endsWith("/"+g.repoId+"/"+g.key)) return null;
        if (v2Mode && (!v2Base.startsWith("/") || g.directory!==v2Base+"/post-apollo-git-map-custody-v2/"+g.repoId+"/"+g.key || !/^(0|[1-9][0-9]{0,19})$/.test(g.device) || !/^(0|[1-9][0-9]{0,19})$/.test(g.inode) || typeof g.device!=="string" || typeof g.inode!=="string" || g.reclamationAllowed!==false)) return null;
        const same=leases.find(l=>l.generation.directory===g.directory);
        if (same) {
            if (same.generation.manifest.snapshot!==g.manifest.snapshot
                    || !["STARTING","HELD"].includes(same.custodyState)) return null;
            if (v2Mode && (same.generation.device!==g.device || same.generation.inode!==g.inode)) return null;
            same.owners++;
            return same;
        }
        // Two active hosts and two replacement generations.
        if (leases.length>=4) return null;
        const l=factory.createObject(root,{generation:g,owners:1,v2Mode:root.v2Mode,v2Base:root.v2Base});
        if (!l) return null;
        leases=leases.concat([l]);
        l.ended.connect(()=>collect(l));
        if (!l.start()) { release(l); return null; }
        return l;
    }
    function collect(l) {
        if (!l || l.owners!==0 || !l.reaped) return;
        leases=leases.filter(item=>item!==l);
        l.destroy();
    }
    function release(l) {
        if (!l || !leases.includes(l) || l.owners<1) return;
        l.owners--;
        if (l.owners===0) {
            l.stop();
            if (l.reaped) collect(l);
        }
    }
}
