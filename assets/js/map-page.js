document.addEventListener("DOMContentLoaded", () => {
  if (typeof L === "undefined" || typeof OZU_MAP_AZA === "undefined") return;

  const GROUP_COLORS = {
    ozu: "#2f6690",
    nagahama: "#2ec4c4",
    hijikawa: "#e08a3c",
    kawabe: "#8a63c2",
  };

  const GSI_TILE = "https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png";
  const GSI_ATTR =
    '<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener">地理院タイル</a>(国土地理院) / 境界データ: 総務省統計局 / <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors';

  function addBaseTiles(map) {
    L.tileLayer(GSI_TILE, { attribution: GSI_ATTR, maxZoom: 18 }).addTo(map);
  }

  function addRiver(map) {
    if (typeof OZU_MAP_RIVER === "undefined") return;
    OZU_MAP_RIVER.forEach((line) => {
      L.polyline(line, { color: "#5aa9d6", weight: 3, opacity: 0.55, interactive: false }).addTo(map);
    });
  }

  function addNeighbors(map) {
    if (typeof OZU_NEIGHBORS === "undefined") return;
    OZU_NEIGHBORS.forEach((n) => {
      (n.lines || []).forEach((line) => {
        L.polyline(line, { color: "#9aa3ab", weight: 1.5, opacity: 0.8, dashArray: "4,4", interactive: false }).addTo(map);
      });
      if (n.label) {
        L.marker(n.label, {
          icon: L.divIcon({ className: "", html: `<span class="neighbor-label">${n.name}</span>` }),
          interactive: false,
        }).addTo(map);
      }
    });
  }

  function popupHtml(title, body) {
    return `<p class="map-popup-title">${title}</p>` + (body ? `<p class="map-popup-body">${body}</p>` : "");
  }

  function displayLabel(name) {
    return name.startsWith("平野町") ? "平野町" : name;
  }

  // 地区が密集して名前が重なる場所は、中心から外向きに引き出し線を伸ばしてラベルを表示する。
  // グループ(大洲/長浜/肱川/河辺)ごとに中心を計算するので、地名マップ(4地域まとめて表示)でも
  // 各地域の外側に向かって線が伸びる自然な配置になる。
  function makeLeaderLabelUpdater(map, dataLayer, leaderLayerGroup, threshold) {
    const BASE_RADIUS = 30;
    const RADIUS_STEP = 15;
    return function updateLeaderLabels() {
      leaderLayerGroup.clearLayers();

      const groupSums = {};
      dataLayer.eachLayer((l) => {
        const p = l.feature.properties;
        const g = p.group || "_all";
        if (!groupSums[g]) groupSums[g] = { sLat: 0, sLng: 0, n: 0 };
        groupSums[g].sLat += p.cy;
        groupSums[g].sLng += p.cx;
        groupSums[g].n++;
      });
      const groupCenters = {};
      Object.keys(groupSums).forEach((g) => {
        const s = groupSums[g];
        groupCenters[g] = [s.sLat / s.n, s.sLng / s.n];
      });

      const layers = [];
      dataLayer.eachLayer((l) => layers.push(l));
      layers.sort((a, b) => a.feature.properties.name.localeCompare(b.feature.properties.name, "ja"));

      const bucketCount = {};
      layers.forEach((l) => {
        const p = l.feature.properties;
        const b = l.getBounds();
        const nw = map.latLngToLayerPoint(b.getNorthWest());
        const se = map.latLngToLayerPoint(b.getSouthEast());
        const wPx = Math.abs(se.x - nw.x);
        const hPx = Math.abs(se.y - nw.y);
        const centroidLatLng = L.latLng(p.cy, p.cx);

        if (Math.min(wPx, hPx) >= threshold) {
          l.bindTooltip(displayLabel(p.name), { permanent: true, direction: "center", className: "aza-label" });
          l.openTooltip();
          return;
        }
        l.unbindTooltip();

        const g = p.group || "_all";
        const centerPt = map.latLngToLayerPoint(groupCenters[g]);
        const centroidPt = map.latLngToLayerPoint(centroidLatLng);
        let angle = Math.atan2(centroidPt.y - centerPt.y, centroidPt.x - centerPt.x);
        // 名前のハッシュで少しだけ角度をずらし、完全な重なりを避ける
        let hash = 0;
        for (let i = 0; i < p.name.length; i++) hash = (hash * 31 + p.name.charCodeAt(i)) % 997;
        angle += ((hash % 11) - 5) * (Math.PI / 90);

        const bucketKey = g + ":" + Math.round(angle / (Math.PI / 8));
        const count = bucketCount[bucketKey] || 0;
        bucketCount[bucketKey] = count + 1;
        const radius = BASE_RADIUS + count * RADIUS_STEP;

        const labelPt = L.point(centroidPt.x + Math.cos(angle) * radius, centroidPt.y + Math.sin(angle) * radius);
        const labelLatLng = map.layerPointToLatLng(labelPt);

        L.polyline([centroidLatLng, labelLatLng], { color: "#6b7684", weight: 1, opacity: 0.7, interactive: false }).addTo(leaderLayerGroup);
        L.marker(labelLatLng, {
          icon: L.divIcon({ className: "", html: `<span class="leader-label">${displayLabel(p.name)}</span>` }),
          interactive: false,
        }).addTo(leaderLayerGroup);
      });
    };
  }

  // ============ Tab1: 地名マップ ============
  let namesMap, namesAzaLayer;
  function initNamesMap() {
    namesMap = L.map("map-names", { scrollWheelZoom: true, minZoom: 10, maxZoom: 17, zoomSnap: 0.25, zoomDelta: 0.5, wheelPxPerZoomLevel: 100 });
    addBaseTiles(namesMap);
    addNeighbors(namesMap);
    addRiver(namesMap);

    namesAzaLayer = L.geoJSON(OZU_MAP_AZA, {
      style: (feature) => {
        const p = feature.properties;
        const base = GROUP_COLORS[p.group] || "#999";
        return { color: base, weight: 1, fillColor: base, fillOpacity: 0.16, opacity: 0.55 };
      },
      onEachFeature: (feature, layer) => {
        const p = feature.properties;
        layer.bindTooltip(displayLabel(p.name), { permanent: true, direction: "center", className: "aza-label" });
        layer.closeTooltip();

        const info = typeof OZU_MAP_INFO !== "undefined" ? OZU_MAP_INFO[p.name] : null;
        const popTitle = info ? info.title : p.name;
        const popBody = info ? info.body : p.pop ? `人口 ${p.pop.toLocaleString()}人(令和2年国勢調査)` : "";
        layer.bindPopup(popupHtml(popTitle, popBody));

        // クリックで詳細(ポップアップ)、ホバーは枠の強調だけ。
        // 以前はmouseoverでポップアップも自動的に開閉していたが、
        // ポリゴンの境界をまたぐたびにopen/closeが連続発火してちらつく原因になっていたため廃止。
        layer.on("mouseover", () => {
          layer.setStyle({ weight: 2, fillOpacity: 0.3 });
        });
        layer.on("mouseout", () => {
          namesAzaLayer.resetStyle(layer);
        });
      },
    }).addTo(namesMap);

    const namesLeaderGroup = L.layerGroup().addTo(namesMap);
    const updateNamesLeaderLabels = makeLeaderLabelUpdater(namesMap, namesAzaLayer, namesLeaderGroup, 46);

    function updateLabels() {
      const zoom = namesMap.getZoom();
      if (zoom >= 13) {
        updateNamesLeaderLabels();
      } else {
        namesAzaLayer.eachLayer((layer) => layer.closeTooltip());
        namesLeaderGroup.clearLayers();
      }
    }
    namesMap.on("zoomend", updateLabels);

    // 以前は特定3地区(highlightフラグ)だけ赤枠にして、そこへ自動ズームしていたが、
    // 「なぜこの3地区だけ強調されるのか分からない」という指摘を受けて廃止。
    // 全地区が均等に見えるよう、大洲市全体の範囲に合わせる。
    const allBounds = namesAzaLayer.getBounds();
    if (allBounds.isValid()) namesMap.fitBounds(allBounds, { padding: [20, 20] });
    updateLabels();
  }

  // ============ Tab2: 旧大洲市 全地区(引き出し線ラベル) ============
  let ozuAllMap, ozuAllLayer, leaderGroup;
  const LEADER_PX_THRESHOLD = 50; // これより小さい地区は引き出し線ラベルにする

  function initOzuAllMap() {
    ozuAllMap = L.map("map-ozuall", { scrollWheelZoom: true, minZoom: 10, maxZoom: 17, zoomSnap: 0.25, zoomDelta: 0.5, wheelPxPerZoomLevel: 100 });
    addBaseTiles(ozuAllMap);
    addRiver(ozuAllMap);

    const ozuOnly = {
      type: "FeatureCollection",
      features: OZU_MAP_AZA.features.filter((f) => f.properties.group === "ozu"),
    };

    leaderGroup = L.layerGroup().addTo(ozuAllMap);

    ozuAllLayer = L.geoJSON(ozuOnly, {
      style: () => ({ color: "#1c4e70", weight: 1.6, fillColor: "#2f6690", fillOpacity: 0.2, opacity: 0.85 }),
      onEachFeature: (feature, l) => {
        const p = feature.properties;
        const info = typeof OZU_MAP_INFO !== "undefined" ? OZU_MAP_INFO[p.name] : null;
        const popBody = info ? info.body : p.pop ? `人口 ${p.pop.toLocaleString()}人(令和2年国勢調査)` : "";
        l.bindPopup(popupHtml(info ? info.title : p.name, popBody));
        // クリックで詳細を見る方式(mouseoverでの自動開閉は隣接ポリゴンの境界でちらつくため廃止)
      },
    }).addTo(ozuAllMap);

    const updateLeaderLabels = makeLeaderLabelUpdater(ozuAllMap, ozuAllLayer, leaderGroup, LEADER_PX_THRESHOLD);

    ozuAllMap.on("zoomend", updateLeaderLabels);

    const b = ozuAllLayer.getBounds();
    if (b.isValid()) ozuAllMap.fitBounds(b, { padding: [20, 20] });
    updateLeaderLabels();
  }

  // ============ Tab4: 学校マップ ============
  let schoolsMap;
  function initSchoolsMap() {
    schoolsMap = L.map("map-schools", { scrollWheelZoom: true, minZoom: 10, maxZoom: 17, zoomSnap: 0.25, zoomDelta: 0.5, wheelPxPerZoomLevel: 100 });
    addBaseTiles(schoolsMap);
    addRiver(schoolsMap);

    if (typeof OZU_FACILITIES === "undefined") return;
    const bounds = L.latLngBounds([]);
    const schoolMarkers = [];
    OZU_FACILITIES.forEach((f) => {
      const icon = L.divIcon({ className: "", html: `<span class="map-emoji-marker">${f.icon}</span>`, iconSize: [26, 26], iconAnchor: [13, 13] });
      const marker = L.marker([f.lat, f.lon], { icon }).addTo(schoolsMap);
      marker.bindTooltip(f.name, { permanent: true, direction: "right", offset: [10, 0], className: "facility-label" });
      marker.bindPopup(popupHtml(f.name, `住所: ${f.addr}(${f.aza}の概算位置)`));
      schoolMarkers.push(marker);
      bounds.extend([f.lat, f.lon]);
    });
    if (bounds.isValid()) schoolsMap.fitBounds(bounds, { padding: [24, 24] });

    // 引いて見ているとき(ズームアウト時)は名前が重なって読めなくなるため、
    // ある程度ズームインした時だけラベルを表示する。
    function updateSchoolLabels() {
      const show = schoolsMap.getZoom() >= 14;
      schoolMarkers.forEach((m) => (show ? m.openTooltip() : m.closeTooltip()));
    }
    schoolsMap.on("zoomend", updateSchoolLabels);
    updateSchoolLabels();
  }

  // ============ Tab5: 橋・トンネル ============
  let bridgesMap;
  const ROAD_COLORS = { trunk: "#c0392b", primary: "#d98c1f" };
  function addRoads(map) {
    if (typeof OZU_ROADS === "undefined") return;
    OZU_ROADS.forEach((g) => {
      const color = ROAD_COLORS[g.kind] || "#999";
      const weight = g.kind === "trunk" ? 4 : 2.5;
      const roadName = (g.kind === "trunk" ? "国道" : "県道") + g.ref + "号";
      (g.segments || []).forEach((seg) => {
        if (seg && seg.length) {
          L.polyline(seg, { color, weight, opacity: 0.65 })
            .addTo(map)
            .bindTooltip(roadName, { sticky: true, className: "facility-label" });
        }
      });
      if (!g.labelAt) return;
      L.marker(g.labelAt, {
        icon: L.divIcon({ className: "", html: `<span class="road-label" style="border-color:${color};color:${color}">${roadName}</span>` }),
      }).addTo(map);
    });
  }

  function initBridgesMap() {
    bridgesMap = L.map("map-bridges", { scrollWheelZoom: true, minZoom: 10, maxZoom: 17, zoomSnap: 0.25, zoomDelta: 0.5, wheelPxPerZoomLevel: 100 });
    addBaseTiles(bridgesMap);
    addRoads(bridgesMap);
    addRiver(bridgesMap);

    if (typeof OZU_BRIDGES === "undefined") return;
    const bounds = L.latLngBounds([]);
    const bridgeMarkers = [];
    OZU_BRIDGES.forEach((b) => {
      const color = b.cat === "tunnel" ? "#7a4fc9" : "#d0453a";
      const icon = L.divIcon({ className: "", html: `<span class="map-poi-marker" style="background:${color}"></span>`, iconSize: [14, 14], iconAnchor: [7, 7] });
      const marker = L.marker([b.lat, b.lon], { icon }).addTo(bridgesMap);
      marker.bindTooltip(b.name, { permanent: true, direction: "top", offset: [0, -6], className: "facility-label" });
      marker.bindPopup(popupHtml(b.name, b.road || ""));
      bridgeMarkers.push(marker);
      bounds.extend([b.lat, b.lon]);
    });
    if (bounds.isValid()) bridgesMap.fitBounds(bounds, { padding: [24, 24] });
    else bridgesMap.setView([33.55, 132.55], 11);

    // 引いて見ているとき(全域表示時)は橋・トンネル名が密集して重なるため、
    // ある程度ズームインした時だけラベルを表示する(学校マップと同じ方式)。
    function updateBridgeLabels() {
      const show = bridgesMap.getZoom() >= 13;
      bridgeMarkers.forEach((m) => (show ? m.openTooltip() : m.closeTooltip()));
    }
    bridgesMap.on("zoomend", updateBridgeLabels);
    updateBridgeLabels();
  }

  // ============ タブ切り替え ============
  const initFns = { names: initNamesMap, ozuall: initOzuAllMap, schools: initSchoolsMap, bridges: initBridgesMap };
  const mapRefs = { names: () => namesMap, ozuall: () => ozuAllMap, schools: () => schoolsMap, bridges: () => bridgesMap };
  const initedTabs = new Set();

  const tabButtons = document.querySelectorAll(".map-tab");
  const panels = document.querySelectorAll(".map-tab-panel");

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      tabButtons.forEach((b) => b.classList.toggle("active", b === btn));
      panels.forEach((p) => p.classList.toggle("active", p.dataset.panel === tab));

      if (initFns[tab] && !initedTabs.has(tab)) {
        initedTabs.add(tab); // 先にマークして多重初期化を防ぐ
        try {
          initFns[tab]();
        } catch (e) {
          console.error("map init failed:", tab, e);
        }
      } else if (mapRefs[tab] && mapRefs[tab]()) {
        setTimeout(() => mapRefs[tab]().invalidateSize(), 50);
      }
    });
  });

  // 最初のタブ(地名マップ)を初期化
  initNamesMap();
  initedTabs.add("names");

  // ============ 地名ポスター ============
  const posterBtns = document.querySelectorAll(".poster-btn");
  const posterImg = document.getElementById("poster-img");
  const posterDownload = document.getElementById("poster-download");
  posterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      posterBtns.forEach((b) => b.classList.toggle("active", b === btn));
      const key = btn.dataset.poster;
      const src = `../assets/img/map-poster-${key}.png`;
      posterImg.src = src;
      posterDownload.href = src;
    });
  });
});
