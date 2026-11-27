// Initial QUICK favorites, not an independent library or a launch API.
// Return fresh records; the future catalog owns persistence and user edits.
// The fixed instruments preserve their current specialized execution contract
// until the Workshop can represent them without dropping evidence.
function initialWorkflowFavorites() {
    const configured = (id,name,durationSeconds,instrument) => ({
        id:id,name:name,favorite:true,execution:"configured",
        plan:{durationSeconds:durationSeconds,instruments:[instrument]}
    });
    const fixed = (id,name,kind) => ({
        id:id,name:name,favorite:true,execution:"fixed",kind:kind
    });
    return [
        configured("default-memory","MEMORY OBSERVE",120,{kind:"memory",intervalMs:10000}),
        fixed("default-inventory","SOURCE WORKLOAD SCAN","inventory"),
        configured("default-threads","THREAD SAMPLE",30,{kind:"threads",intervalMs:1000,topCount:4}),
        configured("default-census","PROCESS CENSUS",30,{kind:"census",intervalMs:10000}),
        configured("default-storage","STORAGE OBSERVE",30,{kind:"storage"}),
        fixed("default-appcontrol","APPCONTROL TEST","appcontrol")
    ];
}
