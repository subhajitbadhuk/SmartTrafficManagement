const laneOrder = [1, 2, 3, 4];

const trafficData = JSON.parse(
    localStorage.getItem("trafficData")
);

console.log("Traffic Data:", trafficData);

if (!trafficData) {
    alert("No traffic data found. Run detection first.");
}

// ============================
// LOAD IMAGES
// ============================

loadImages();
showVehicleData();
startSignalCycle();

function loadImages() {

    document.getElementById("lane1Img").src =
        trafficData.lane1_image + "?t=" + Date.now();

    document.getElementById("lane2Img").src =
        trafficData.lane2_image + "?t=" + Date.now();

    document.getElementById("lane3Img").src =
        trafficData.lane3_image + "?t=" + Date.now();

    document.getElementById("lane4Img").src =
        trafficData.lane4_image + "?t=" + Date.now();
}

// ============================
// SHOW DATA
// ============================

function showVehicleData() {

    updateLane(1, trafficData.lane1);
    updateLane(2, trafficData.lane2);
    updateLane(3, trafficData.lane3);
    updateLane(4, trafficData.lane4);
}

function updateLane(laneNo, data) {

    const score =
        (data.cars * 1) +
        (data.buses * 3) +
        (data.trucks * 4) +
        (data.motorcycles * 0.5);

    document.getElementById(
        `lane${laneNo}Total`
    ).innerHTML =
        `Traffic Score: ${Math.round(score)}
        <br>
        Total Vehicles: ${data.total}`;

    document.getElementById(
        `lane${laneNo}Cars`
    ).innerHTML =
        `Cars: ${data.cars}`;

    document.getElementById(
        `lane${laneNo}Bus`
    ).innerHTML =
        `Buses: ${data.buses}`;

    document.getElementById(
        `lane${laneNo}Truck`
    ).innerHTML =
        `Trucks: ${data.trucks}`;

    document.getElementById(
        `lane${laneNo}Bike`
    ).innerHTML =
        `Motorcycles: ${data.motorcycles}`;
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
                (laneData.cars * 1) +
                (laneData.buses * 3) +
                (laneData.trucks * 4) +
                (laneData.motorcycles * 0.5);

            const greenTime =
                Math.min(
                    Math.max(
                        Math.round(weightedCount),
                        10
                    ),
                    40
                );

            console.log(
                `Lane ${lane} -> ${greenTime}s`
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

function activateLane(
    laneNo,
    seconds
) {

    return new Promise((resolve) => {

        for (let i = 1; i <= 4; i++) {

            const card =
                document.getElementById(
                    `lane${i}Card`
                );

            card.classList.remove(
                "active"
            );

            card.classList.add(
                "waiting"
            );

            document.getElementById(
                `lane${i}Status`
            ).innerText =
                "WAITING";

            document.getElementById(
                `lane${i}Timer`
            ).innerText =
                "0s";
        }

        const activeCard =
            document.getElementById(
                `lane${laneNo}Card`
            );

        activeCard.classList.remove(
            "waiting"
        );

        activeCard.classList.add(
            "active"
        );

        document.getElementById(
            `lane${laneNo}Status`
        ).innerText =
            "ACTIVE";

        let timer = seconds;

        const interval =
            setInterval(() => {

                document.getElementById(
                    `lane${laneNo}Timer`
                ).innerText =
                    timer + "s";

                timer--;

                if (timer < 0) {

                    clearInterval(
                        interval
                    );

                    resolve();
                }

            }, 1000);

    });
}