const state = {
  directions: [],
  activeDirection: null,
  audioContext: null,
  decodedWaveforms: new Map(),
};

const panel = document.querySelector("#samplePanel");
const outboundTabs = document.querySelector("#outboundTabs");
const inboundTabs = document.querySelector("#inboundTabs");

function makeTab(direction) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "direction-tab";
  button.id = `tab-${direction.id}`;
  button.role = "tab";
  button.setAttribute("aria-controls", "samplePanel");
  button.setAttribute("aria-selected", "false");
  button.textContent = direction.short_label.replace(" to ", " → ");
  button.addEventListener("click", () => selectDirection(direction.id, true));
  button.addEventListener("keydown", handleTabKeydown);
  return button;
}

function handleTabKeydown(event) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  const tabs = [...document.querySelectorAll(".direction-tab")];
  const current = tabs.indexOf(event.currentTarget);
  let next = current;
  if (event.key === "ArrowLeft") next = (current - 1 + tabs.length) % tabs.length;
  if (event.key === "ArrowRight") next = (current + 1) % tabs.length;
  if (event.key === "Home") next = 0;
  if (event.key === "End") next = tabs.length - 1;
  event.preventDefault();
  tabs[next].focus();
  tabs[next].click();
}

function createAudioCell(label, source, sampleId, kind) {
  const cell = document.createElement("div");
  cell.className = "audio-cell";

  const mobileLabel = document.createElement("p");
  mobileLabel.className = "audio-cell-label";
  mobileLabel.textContent = label;

  const canvas = document.createElement("canvas");
  canvas.className = "waveform";
  canvas.width = 620;
  canvas.height = 84;
  canvas.dataset.source = source;
  canvas.setAttribute("aria-hidden", "true");

  const audio = document.createElement("audio");
  audio.controls = true;
  audio.preload = "metadata";
  audio.src = source;
  audio.setAttribute("aria-label", `${label}, ${sampleId}`);
  audio.addEventListener("play", stopOtherAudio);

  cell.append(mobileLabel, canvas, audio);
  requestWaveform(canvas, kind);
  return cell;
}

function stopOtherAudio(event) {
  document.querySelectorAll("audio").forEach((audio) => {
    if (audio !== event.currentTarget && !audio.paused) audio.pause();
  });
}

function renderDirection(direction) {
  const fragment = document.createDocumentFragment();
  const header = document.createElement("div");
  header.className = "panel-header";
  header.innerHTML = `
    <div>
      <p class="direction-code">${direction.source_code} → ${direction.target_code}</p>
      <h3>${direction.source} to ${direction.target}</h3>
    </div>
    <p class="headphone-note">${direction.samples.length} paired examples</p>
  `;

  const headings = document.createElement("div");
  headings.className = "column-headings";
  headings.innerHTML = "<span>Utterance</span><span>Original speech</span><span>PHONOS conversion</span>";

  fragment.append(header, headings);
  direction.samples.forEach((sample) => {
    const row = document.createElement("article");
    row.className = "sample-row";
    row.innerHTML = `
      <div class="sample-info">
        <p class="sample-label">${sample.label}</p>
        <p class="transcript"></p>
      </div>
    `;
    row.querySelector(".transcript").textContent = sample.transcript;
    row.append(
      createAudioCell("Original speech", sample.original_audio, sample.label, "original"),
      createAudioCell("PHONOS conversion", sample.converted_audio, sample.label, "converted")
    );
    fragment.append(row);
  });

  panel.replaceChildren(fragment);
}

function selectDirection(directionId, updateHash = false) {
  const direction = state.directions.find((item) => item.id === directionId);
  if (!direction) return;
  state.activeDirection = directionId;
  document.querySelectorAll(".direction-tab").forEach((tab) => {
    tab.setAttribute("aria-selected", String(tab.id === `tab-${directionId}`));
    tab.tabIndex = tab.id === `tab-${directionId}` ? 0 : -1;
  });
  renderDirection(direction);
  if (updateHash) history.replaceState(null, "", `#${directionId}`);
}

function drawPlaceholder(canvas, color) {
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.strokeStyle = color;
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(0, canvas.height / 2);
  context.lineTo(canvas.width, canvas.height / 2);
  context.stroke();
}

async function drawWaveform(canvas, kind) {
  const source = canvas.dataset.source;
  const color = kind === "converted" ? "#0b6f69" : "#747b82";
  drawPlaceholder(canvas, color);
  try {
    let values = state.decodedWaveforms.get(source);
    if (!values) {
      const response = await fetch(source);
      if (!response.ok) throw new Error(`Audio request failed: ${response.status}`);
      state.audioContext ??= new AudioContext();
      const buffer = await state.audioContext.decodeAudioData(await response.arrayBuffer());
      const channel = buffer.getChannelData(0);
      const points = 310;
      const block = Math.max(1, Math.floor(channel.length / points));
      values = Array.from({ length: points }, (_, index) => {
        let peak = 0;
        const start = index * block;
        const end = Math.min(channel.length, start + block);
        for (let sample = start; sample < end; sample += 1) {
          peak = Math.max(peak, Math.abs(channel[sample]));
        }
        return peak;
      });
      state.decodedWaveforms.set(source, values);
    }

    if (!canvas.isConnected) return;
    const context = canvas.getContext("2d");
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = color;
    const center = canvas.height / 2;
    const xStep = canvas.width / values.length;
    values.forEach((value, index) => {
      const height = Math.max(2, value * canvas.height * 0.88);
      context.fillRect(index * xStep, center - height / 2, Math.max(1, xStep - 1), height);
    });
  } catch (error) {
    console.warn(`Could not draw waveform for ${source}`, error);
  }
}

function requestWaveform(canvas, kind) {
  if (!("IntersectionObserver" in window)) {
    drawWaveform(canvas, kind);
    return;
  }
  const observer = new IntersectionObserver(
    (entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      drawWaveform(canvas, kind);
    },
    { rootMargin: "240px" }
  );
  observer.observe(canvas);
}

async function initialize() {
  try {
    const response = await fetch("samples.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Sample manifest request failed: ${response.status}`);
    const manifest = await response.json();
    state.directions = manifest.directions;
    state.directions.forEach((direction, index) => {
      const tab = makeTab(direction);
      (index < 3 ? outboundTabs : inboundTabs).append(tab);
    });
    const requestedDirection = window.location.hash.slice(1);
    const initial = state.directions.some((item) => item.id === requestedDirection)
      ? requestedDirection
      : state.directions[0].id;
    selectDirection(initial);
  } catch (error) {
    panel.innerHTML = `<p class="error-message">The audio samples could not be loaded. ${error.message}</p>`;
  }
}

initialize();
