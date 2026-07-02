const laneOrder = [1, 2, 3, 4];

const trafficData = JSON.parse(
    localStorage.getItem("trafficData")
);

const uploadedImagePreviews = JSON.parse(
    localStorage.getItem("uploadedImagePreviews") || "{}"
);

if (!trafficData) {
    alert("No traffic data found. Please run detection first.");
    window.location.href = "index.html";
}

// ============================
// LOAD PAGE
// ============================

if (trafficData) {
    loadImages();
    showVehicleData();
    startSignalCycle();
}

// ============================
// LOAD DETECTED IMAGES
// ============================

function loadImages() {

    for (let i = 1; i <= 4; i++) {

        const imageElement =
            document.getElementById(`lane${i}Img`);

        const laneName =
            `lane${i}`;

        const detectedImage =
            trafficData[`${laneName}_image`];

        const originalPreview =
            uploadedImagePreviews[laneName];

        imageElement.onerror = function () {

            if (originalPreview && imageElement.src !== originalPreview) {

                imageElement.src = originalPreview;

            }

        };

        if (detectedImage) {

            imageElement.src =
                detectedImage + "?t=" + Date.now();

        }

        else if (originalPreview) {

            imageElement.src = originalPreview;

        }

    }

}

// ============================
// SHOW VEHICLE DATA
// ============================

function showVehicleData() {

    updateLane(1, trafficData.lane1);
    updateLane(2, trafficData.lane2);
    updateLane(3, trafficData.lane3);
    updateLane(4, trafficData.lane4);

}

function updateLane(laneNo, data) {

    if (!data) return;

    const score =
        (data.cars * 2) +
        (data.buses * 5) +
        (data.trucks * 5) +
        (data.motorcycles * 1) +
        (data.autorickshaws * 2) +
        (data.bicycles * 1);

    document.getElementById(`lane${laneNo}Total`).innerHTML =
        `
        <b>Traffic Score:</b> ${Math.round(score)}<br>
        <b>Total Vehicles:</b> ${data.total}
        `;

    document.getElementById(`lane${laneNo}Cars`).innerHTML =
        `Cars : ${data.cars}`;

    document.getElementById(`lane${laneNo}Bus`).innerHTML =
        `Buses : ${data.buses}`;

    document.getElementById(`lane${laneNo}Truck`).innerHTML =
        `Trucks : ${data.trucks}`;

    document.getElementById(`lane${laneNo}Bike`).innerHTML =
        `Motorcycles : ${data.motorcycles}`;

    const autoElement =
        document.getElementById(`lane${laneNo}Auto`);

    if (autoElement) {

        autoElement.innerHTML =
            `Auto Rickshaws : ${data.autorickshaws}`;

    }

    const bicycleElement =
        document.getElementById(`lane${laneNo}Bicycle`);

    if (bicycleElement) {

        bicycleElement.innerHTML =
            `Bicycles : ${data.bicycles}`;

    }

}

// ============================
// SIGNAL LOOP
// ============================

async function startSignalCycle() {

    while (true) {

        for (let lane of laneOrder) {

            const laneData =
                trafficData[`lane${lane}`];

            const weightedCount =
                (laneData.cars * 2) +
                (laneData.buses * 5) +
                (laneData.trucks * 5) +
                (laneData.motorcycles * 1) +
                (laneData.autorickshaws * 2) +
                (laneData.bicycles * 1);

            const greenTime =
                Math.min(
                    Math.max(
                        Math.round(weightedCount),
                        10
                    ),
                    40
                );

            await activateLane(
                lane,
                greenTime
            );

        }

    }

}

// ============================
// ACTIVATE LANE
// ============================

function activateLane(laneNo, seconds) {

    return new Promise((resolve) => {

        for (let i = 1; i <= 4; i++) {

            const card =
                document.getElementById(`lane${i}Card`);

            card.classList.remove("active");
            card.classList.add("waiting");

            document.getElementById(`lane${i}Status`).innerText =
                "WAITING";

            document.getElementById(`lane${i}Timer`).innerText =
                "0s";

        }

        const activeCard =
            document.getElementById(`lane${laneNo}Card`);

        activeCard.classList.remove("waiting");
        activeCard.classList.add("active");

        document.getElementById(`lane${laneNo}Status`).innerText =
            "ACTIVE";

        let timer = seconds;

        document.getElementById(`lane${laneNo}Timer`).innerText =
            timer + "s";

        const interval = setInterval(() => {

            timer--;

            document.getElementById(`lane${laneNo}Timer`).innerText =
                timer + "s";

            if (timer <= 0) {

                clearInterval(interval);

                resolve();

            }

        }, 1000);

    });

}
