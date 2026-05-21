import assert from "node:assert/strict";
import {
  addAssetLayerToScene,
  addPreviewReviewMarker,
  blankProject,
  normalizeTimelineMarkers,
  previewExportReadiness,
  ProjectData,
  setSceneReviewStatus,
  totalTimelineDuration,
  updateSceneTimingAdvanced
} from "./project";

function baseProject(): ProjectData {
  return {
    project: { width: 1280, height: 720, fps: 30, duration: 4 },
    assets: {
      clip: "assets/clip.mp4",
      music: "assets/music.wav"
    },
    timeline: [
      { id: "intro", start: 0, duration: 2, layers: [{ type: "text", text: "Intro" }] },
      { id: "main", start: 2, duration: 2, layers: [{ type: "video", asset: "clip" }] }
    ],
    audio: []
  };
}

function testNormalizeTimelineMarkers() {
  const markers = normalizeTimelineMarkers(
    [
      { time: "1.25", sceneId: "intro", type: "beat", label: "Beat 1" },
      { time: Number.NaN, note: "Needs trim", type: "needs_cut", resolved: true },
      null,
      "bad"
    ],
    "marker",
    true
  );

  assert.equal(markers.length, 2);
  assert.deepEqual(markers[0], {
    time: 1.25,
    sceneId: "intro",
    type: "beat",
    label: "Beat 1",
    note: undefined,
    resolved: undefined,
    id: undefined
  });
  assert.equal(markers[1].time, 0);
  assert.equal(markers[1].sceneId, "marker");
  assert.equal(markers[1].label, "Needs trim");
  assert.equal(markers[1].resolved, true);
}

function testTimelineTimingRippleAndSnap() {
  const project = baseProject();
  const next = updateSceneTimingAdvanced(project, 0, { duration: 2.37 }, { ripple: true, snapSeconds: 0.25 });

  assert.equal(next.timeline?.[0].duration, 2.25);
  assert.equal(next.timeline?.[1].start, 2.25);
  assert.equal(next.project?.duration, 4.25);
  assert.equal(project.timeline?.[0].duration, 2);
  assert.equal(project.timeline?.[1].start, 2);
}

function testPreviewReadinessAndMarkerResolution() {
  let project = baseProject();
  project = addPreviewReviewMarker(project, { type: "needs_cut", time: 0.6, sceneId: "intro", note: "Trim opener" });

  let readiness = previewExportReadiness(project);
  assert.equal(readiness.active, true);
  assert.equal(readiness.ready, false);
  assert.equal(readiness.warnings.some((warning) => warning.includes("needs cut")), true);

  project = setSceneReviewStatus(project, "intro", "approved");
  project = setSceneReviewStatus(project, "main", "locked");
  readiness = previewExportReadiness(project);

  assert.equal(readiness.ready, true);
  assert.equal(readiness.approved, 2);
  assert.equal(readiness.total, 2);
}

function testAssetInsertionKeepsJsonShape() {
  let project = baseProject();
  project = addAssetLayerToScene(project, 1, "music");

  assert.equal(project.audio?.length, 1);
  assert.equal(project.audio?.[0].asset, "music");
  assert.equal(project.timeline?.[1].layers.length, 1);

  project = addAssetLayerToScene(project, 1, "clip");
  assert.equal(project.timeline?.[1].layers.length, 2);
  assert.equal(project.timeline?.[1].layers[1].type, "video");
}

function testBlankProjectDuration() {
  const project = blankProject();
  assert.equal(totalTimelineDuration(project), 8);
}

testNormalizeTimelineMarkers();
testTimelineTimingRippleAndSnap();
testPreviewReadinessAndMarkerResolution();
testAssetInsertionKeepsJsonShape();
testBlankProjectDuration();

console.log("project helper tests passed");
