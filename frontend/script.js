console.log("Smart Traffic Loaded");

// =====================================
// POLYGON STORAGE
// =====================================

const polygons = {
    lane1: [],
    lane2: [],
    lane3: [],
    lane4: []
};

const uploadedImagePreviews = {
    lane1: "",
    lane2: "",
    lane3: "",
    lane4: ""
};

// =====================================
// CANVAS SETUP
// =====================================

setupCanvas("lane1Input", "canvas1", polygons.lane1, "lane1");
setupCanvas("lane2Input", "canvas2", polygons.lane2, "lane2");
setupCanvas("lane3Input", "canvas3", polygons.lane3, "lane3");
setupCanvas("lane4Input", "canvas4", polygons.lane4, "lane4");

// =====================================
// MAIN FUNCTION
// =====================================

function setupCanvas(inputId, canvasId, polygonArray, laneName) {

    const input = document.getElementById(inputId);
    const canvas = document.getElementById(canvasId);
    const ctx = canvas.getContext("2d");

    let img = new Image();

    input.addEventListener("change", function () {

        const file = this.files[0];

        if (!file) return;

        const reader = new FileReader();

        reader.onload = function (e) {

            img.onload = function () {

                canvas.width = img.width;
                canvas.height = img.height;

                ctx.clearRect(
                    0,
                    0,
                    canvas.width,
                    canvas.height
                );

                ctx.drawImage(
                    img,
                    0,
                    0
                );

                polygonArray.length = 0;

                uploadedImagePreviews[laneName] =
                    createPreviewDataUrl(img);
            };

            img.src = e.target.result;
        };

        reader.readAsDataURL(file);
    });

    canvas.addEventListener("click", function (event) {

        if (!img.src) return;

        const rect = canvas.getBoundingClientRect();

        const scaleX =
            canvas.width / rect.width;

        const scaleY =
            canvas.height / rect.height;

        const x =
            (event.clientX - rect.left) * scaleX;

        const y =
            (event.clientY - rect.top) * scaleY;

        polygonArray.push({
            x: x,
            y: y
        });

        redrawCanvas(
            canvas,
            ctx,
            img,
            polygonArray
        );
    });

}

function createPreviewDataUrl(img) {

    const maxSize = 900;
    const scale =
        Math.min(
            maxSize / img.width,
            maxSize / img.height,
            1
        );

    const previewCanvas =
        document.createElement("canvas");

    previewCanvas.width =
        Math.round(img.width * scale);

    previewCanvas.height =
        Math.round(img.height * scale);

    const previewContext =
        previewCanvas.getContext("2d");

    previewContext.drawImage(
        img,
        0,
        0,
        previewCanvas.width,
        previewCanvas.height
    );

    return previewCanvas.toDataURL(
        "image/jpeg",
        0.75
    );

}

// =====================================
// REDRAW
// =====================================

function redrawCanvas(
    canvas,
    ctx,
    img,
    points
) {

    ctx.clearRect(
        0,
        0,
        canvas.width,
        canvas.height
    );

    ctx.drawImage(
        img,
        0,
        0
    );

    for (let i = 0; i < points.length; i++) {

        ctx.beginPath();

        ctx.arc(
            points[i].x,
            points[i].y,
            6,
            0,
            Math.PI * 2
        );

        ctx.fillStyle = "red";
        ctx.fill();
    }

    if (points.length > 1) {

        ctx.beginPath();

        ctx.moveTo(
            points[0].x,
            points[0].y
        );

        for (let i = 1; i < points.length; i++) {

            ctx.lineTo(
                points[i].x,
                points[i].y
            );
        }

        ctx.strokeStyle = "cyan";
        ctx.lineWidth = 4;
        ctx.stroke();
    }

    if (points.length >= 3) {

        ctx.beginPath();

        ctx.moveTo(
            points[0].x,
            points[0].y
        );

        for (let i = 1; i < points.length; i++) {

            ctx.lineTo(
                points[i].x,
                points[i].y
            );
        }

        ctx.closePath();

        ctx.fillStyle =
            "rgba(0,255,255,0.15)";

        ctx.fill();
    }
}

// =====================================
// SAVE POLYGONS
// =====================================

document
.getElementById("savePolygonsBtn")
.addEventListener(
    "click",
    function () {

        localStorage.setItem(
            "lanePolygons",
            JSON.stringify(polygons)
        );

        alert(
            "Lane Areas Saved Successfully"
        );
    }
);

// =====================================
// PROCESS TRAFFIC
// =====================================

document
.getElementById("processTrafficBtn")
.addEventListener(
    "click",
    async function () {

        try {

            const loading =
                document.getElementById("loadingBox");

            if (loading)
                loading.style.display = "block";

            // -----------------------------
            // Check all images selected
            // -----------------------------

            const lane1 =
                document.getElementById("lane1Input").files[0];

            const lane2 =
                document.getElementById("lane2Input").files[0];

            const lane3 =
                document.getElementById("lane3Input").files[0];

            const lane4 =
                document.getElementById("lane4Input").files[0];

            if (!lane1 || !lane2 || !lane3 || !lane4) {

                alert("Please select all four lane images.");

                loading.style.display = "none";

                return;
            }

            try {

                localStorage.setItem(
                    "uploadedImagePreviews",
                    JSON.stringify(uploadedImagePreviews)
                );

            }

            catch (storageError) {

                console.warn(
                    "Image previews could not be saved.",
                    storageError
                );

            }

            // -----------------------------
            // Upload Images
            // -----------------------------

            const formData = new FormData();

            formData.append("lane1", lane1);
            formData.append("lane2", lane2);
            formData.append("lane3", lane3);
            formData.append("lane4", lane4);

            const uploadResponse =
                await fetch(
                    "http://127.0.0.1:5000/upload",
                    {
                        method: "POST",
                        body: formData
                    }
                );

            const uploadData =
                await uploadResponse.json();

            console.log(uploadData);

            if (!uploadResponse.ok) {

                alert(uploadData.error);

                loading.style.display = "none";

                return;
            }

            // -----------------------------
            // Process Images
            // -----------------------------

            const response =
                await fetch(
                    "http://127.0.0.1:5000/process",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify(polygons)
                    }
                );

            const data =
                await response.json();
                if (loading)
                    loading.style.display = "none";

            console.log(data);

            if (!response.ok) {

                alert("Traffic processing failed.");

                loading.style.display = "none";

                return;
            }

            localStorage.setItem(
                "trafficData",
                JSON.stringify(data)
            );

            window.location.href = "live.html";

        }

        catch (error) {

            console.error(error);

            alert("Traffic Processing Failed");

            const loading =
                document.getElementById("loadingBox");

            if (loading)
                loading.style.display = "none";
        }

    }
);
