const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fs = require("fs");
const path = require("path");
const fa = require("react-icons/fa");
// Optional: a helper that writes THEME colours into the deck theme (set APPLY_THEME to its path).
const applyTheme = process.env.APPLY_THEME ? require(process.env.APPLY_THEME).applyTheme : async () => {};

// Usage: node scripts/build_deck.js docs/presentation/NC-Preflight.pptx  (needs pptxgenjs, react, react-dom, react-icons, sharp)
const S = path.join(__dirname, "..", "docs", "presentation", "assets");
const OUT = process.argv[2] || path.join(__dirname, "..", "docs", "presentation", "NC-Preflight.pptx");
const speed = JSON.parse(fs.readFileSync(path.join(S, "speed.json")));

// ------------------------------------------------------------------ theme
const THEME = {
  name: "Machine Shop",
  headFontFace: "Arial",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1C2127", lt1: "FFFFFF", dk2: "2D3540", lt2: "EEF1F4",
    accent1: "F28C28", accent2: "1F8A70", accent3: "5B6670",
    accent4: "D9483B", accent5: "3A7CA5", accent6: "F2C14E",
    hlink: "3A7CA5", folHlink: "5B6670",
  },
};
const HEX = THEME.colors;
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.title = "NC Pre-flight";
pres.author = "Harsh";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const W = 13.333, H = 7.5, MX = 0.6;

// ------------------------------------------------------------------ icons
async function icon(name, color, size = 256) {
  const Comp = fa[name] || fa.FaCircle;
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).resize(size, size).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}
// icon inside a filled circle (the deck's motif)
async function badge(slide, name, x, y, d, fill, fg, objectName) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" }, objectName: objectName + " circle" });
  const p = d * 0.26;
  slide.addImage({ data: await icon(name, fg), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p, objectName: objectName + " icon", altText: "" });
}

// ------------------------------------------------------------------ layouts
pres.defineSlideMaster({
  title: "Cover",
  background: { color: HEX.dk1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 2.05, w: 6.9, h: 1.6, fontSize: 54, bold: true, color: C.background1, align: "left", valign: "bottom", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: MX, y: 3.8, w: 6.6, h: 1.3, fontSize: 22, color: C.accent1, align: "left", valign: "top", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "meta", type: "body", x: MX, y: 6.3, w: 6.6, h: 0.5, fontSize: 13, color: "B9C2CC", valign: "middle", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "Content",
  background: { color: HEX.lt1 },
  margin: [0.5, 0.6, 0.5, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 0.4, w: W - 2 * MX, h: 0.9, fontSize: 34, bold: true, color: C.text1, valign: "middle", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: W - 1.0, y: H - 0.5, w: 0.5, h: 0.3, fontSize: 10, color: "8A949E", align: "right" },
});
pres.defineSlideMaster({
  title: "Closing",
  background: { color: HEX.dk1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 2.3, w: W - 2 * MX, h: 1.3, fontSize: 54, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: MX, y: 3.7, w: W - 2 * MX, h: 0.8, fontSize: 22, color: C.accent1, align: "center", valign: "top", margin: 0 }, text: "" } },
  ],
});

const T = (s) => ({ isTextBox: true, margin: 0, ...s });
const content = (section, title) => {
  const s = pres.addSlide({ masterName: "Content", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  return s;
};
const card = (s, x, y, w, h, fill, name) =>
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { type: "none" }, objectName: name });
const SIM = (s, x, y, w = 3.2) =>
  s.addText("SIMULATED DATA", T({ x, y, w, h: 0.32, fontSize: 11, bold: true, color: C.accent1, charSpacing: 2 }));

(async () => {
  // ================================================================ 1 cover
  pres.addSection({ title: "Introduction" });
  let s = pres.addSlide({ masterName: "Cover", sectionTitle: "Introduction" });
  s.addImage({ path: path.join(S, "hero.png"), x: 6.93, y: 1.96, w: 5.9, h: 3.58, objectName: "Tool path drawing", altText: "3D view of a surface-finishing tool path drawn by the tool from a sample program" });
  s.addText("NC Pre-flight", { placeholder: "title" });
  s.addText("Know how long a CNC job will take, before you cut", { placeholder: "body" });
  s.addText("Portfolio project  ·  Harsh  ·  MIT Manipal  ·  November 2026", { placeholder: "meta" });
  s.addNotes("This is NC Pre-flight. In one line: you give it a CNC machine's program, and before the machine runs it, the tool tells you how long the job will take, how much energy it will use, how sure it is, and whether the program has obvious mistakes. The orange drawing is a 3D surface-finishing tool path drawn from one of the sample programs.");

  // ================================================================ 2 what is CNC
  s = content("Introduction", "First, what is a CNC machine?");
  s.addText([
    { text: "A CNC machine is a computer-controlled cutting machine. ", options: { bold: true } },
    { text: "It carves metal or plastic into parts by moving a spinning tool along a path.", options: { breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 8 } },
    { text: "The path is written as a program of short lines called G-code. ", options: { bold: true } },
    { text: "Each line says where to move and how fast.", options: {} },
  ], T({ x: MX, y: 1.6, w: 5.6, h: 2.2, fontSize: 18, color: C.text2, valign: "top", paraSpaceAfter: 6 }));
  // code card
  card(s, 6.75, 1.55, 5.95, 4.95, HEX.dk1, "G-code card");
  const code = [
    ["G21 G90", "use millimetres, absolute positions"],
    ["S8000 M3", "spin the tool at 8,000 rpm"],
    ["G0 X10 Y0", "move fast to the start (not cutting)"],
    ["G1 Z-2 F300", "go 2 mm into the part, slowly"],
    ["G1 X60 F1200", "cut a straight line at 1,200 mm/min"],
    ["G3 X70 Y10 I0 J10", "cut a curve"],
    ["M30", "end of program"],
  ];
  code.forEach(([c, d], i) => {
    s.addText(c, T({ x: 7.05, y: 1.85 + i * 0.64, w: 2.45, h: 0.5, fontFace: "Courier New", fontSize: 15, bold: true, color: C.accent1, valign: "middle" }));
    s.addText(d, T({ x: 9.6, y: 1.85 + i * 0.64, w: 2.9, h: 0.5, fontSize: 13, color: "D5DCE3", valign: "middle" }));
  });
  await badge(s, "FaIndustry", MX, 4.35, 0.9, HEX.lt2, HEX.dk2, "Factory");
  s.addText("Used everywhere parts are made: cars, aircraft, moulds, medical implants. Small job shops run them all day for many different customers.",
    T({ x: MX + 1.15, y: 4.3, w: 4.4, h: 1.2, fontSize: 15, color: C.text2, valign: "middle" }));
  s.addNotes("Quick background for anyone new to this. A CNC machine follows a program line by line. G0 means move fast without cutting, G1 means cut in a straight line at the feed speed F, G2 and G3 cut curves. That's all you need to follow the rest.");

  // ================================================================ 3 question
  pres.addSection({ title: "The problem" });
  s = content("The problem", "Every shop asks: how long will this job take?");
  const why = [
    ["FaRupeeSign", "Price the job", "Machine time is most of the cost. Guess low and you lose money on every part."],
    ["FaCalendarAlt", "Plan the day", "Which machine is free when? A wrong time estimate breaks the whole schedule."],
    ["FaBolt", "Know the energy", "Electricity per part is rarely estimated at all, yet it is a real cost."],
  ];
  for (let i = 0; i < 3; i++) {
    const x = MX + i * 4.1;
    card(s, x, 1.65, 3.8, 3.3, HEX.lt2, "Reason card " + (i + 1));
    await badge(s, why[i][0], x + 0.35, 1.95, 0.95, HEX.accent1, "FFFFFF", why[i][1]);
    s.addText(why[i][1], T({ x: x + 0.35, y: 3.05, w: 3.1, h: 0.5, fontSize: 21, bold: true, color: C.text1 }));
    s.addText(why[i][2], T({ x: x + 0.35, y: 3.6, w: 3.15, h: 1.2, fontSize: 15, color: C.text2, valign: "top" }));
  }
  card(s, MX, 5.3, W - 2 * MX, 1.15, HEX.dk1, "Today's answer");
  s.addText([
    { text: "Today's answer:  ", options: { bold: true, color: C.accent1 } },
    { text: "the design software (CAM) divides the path length by the cutting speed.  ", options: { color: C.background1 } },
    { text: "Simple, and usually too low.", options: { bold: true, color: C.background1 } },
  ], T({ x: MX + 0.4, y: 5.3, w: W - 2 * MX - 0.8, h: 1.15, fontSize: 18, valign: "middle" }));
  s.addNotes("Why the time matters: the quote, the schedule and the energy bill all depend on it. The usual estimate is length divided by speed. The next slide shows why that is too optimistic.");

  // ================================================================ 4 why too low
  s = content("The problem", "Why length ÷ speed is too optimistic");
  await badge(s, "FaCarSide", MX, 1.65, 0.95, HEX.lt2, HEX.dk2, "Car");
  s.addText("Think of driving.", T({ x: MX + 1.2, y: 1.65, w: 3.6, h: 0.95, fontSize: 21, bold: true, color: C.text1, valign: "middle" }));
  s.addText([
    { text: "A 100 km/h speed limit doesn't mean you drive at 100 on a twisting mountain road. You slow down for every bend and speed up again after.", options: { breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 8 } },
    { text: "A CNC machine is the same. ", options: { bold: true } },
    { text: "It must brake before corners and accelerate after them, so on busy paths it never reaches the programmed speed.", options: {} },
  ], T({ x: MX, y: 2.8, w: 4.3, h: 3.0, fontSize: 16, color: C.text2, valign: "top" }));
  s.addChart(pres.charts.LINE, [
    { name: "Programmed speed", labels: speed.x, values: speed.prog },
    { name: "Real speed (planner)", labels: speed.x, values: speed.actual },
  ], {
    x: 5.2, y: 1.5, w: 7.55, h: 4.3, objectName: "Speed along the path chart",
    chartColors: [HEX.accent3, HEX.accent1], lineSize: 3, lineDataSymbol: "none",
    showTitle: true, title: "Tool speed along a path: a straight run, then a zigzag, then straight", titleFontSize: 14, titleColor: HEX.dk2, titleFontFace: "+mn-lt",
    showLegend: true, legendPos: "b", legendFontSize: 12, legendFontFace: "+mn-lt", legendColor: HEX.dk2,
    catAxisTitle: "Distance along the path (mm)", showCatAxisTitle: true, catAxisTitleFontSize: 12, catAxisTitleColor: "5B6670",
    valAxisTitle: "mm/min", showValAxisTitle: true, valAxisTitleFontSize: 12, valAxisTitleColor: "5B6670",
    catAxisLabelColor: "5B6670", valAxisLabelColor: "5B6670", catAxisLabelFontSize: 11, valAxisLabelFontSize: 11,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", catAxisLabelFrequency: 10,
    valAxisMinVal: 0, valAxisMaxVal: 7000, valAxisMajorUnit: 2000,
    valGridLine: { color: "E3E7EB", size: 0.75 }, catGridLine: { style: "none" },
  });
  card(s, 5.2, 6.0, 7.55, 0.85, HEX.lt2, "Result callout");
  s.addText([
    { text: "+25 %  ", options: { bold: true, color: C.accent1, fontSize: 24 } },
    { text: "this path takes 3.9 s, not the 3.1 s that length ÷ speed predicts", options: { color: C.text2, fontSize: 15 } },
  ], T({ x: 5.45, y: 6.0, w: 7.2, h: 0.85, valign: "middle" }));
  s.addNotes("The grey dashed line is what the program asks for, 6,000 mm/min. The orange line is what the machine can actually do according to the motion planner I wrote: it reaches full speed on the straight part, then in the zigzag it keeps braking for corners. Over this short path that's 25 percent longer than the simple estimate. Real programs have thousands of these corners.");

  // ================================================================ 5 idea
  pres.addSection({ title: "The idea" });
  s = content("The idea", "The basic idea in three steps");
  const steps = [
    ["FaFileCode", "Read the program", "Understand every line: where the tool goes, how fast, when it is cutting."],
    ["FaTachometerAlt", "Simulate the motion", "Work out how the machine really accelerates and brakes, corner by corner. This gives a physics-based time and energy."],
    ["FaBullseye", "Learn the gap, give a range", "Physics alone still misses things. Learn the leftover gap from past runs and answer with a range, not one number."],
  ];
  for (let i = 0; i < 3; i++) {
    const x = MX + i * 4.15;
    s.addText(String(i + 1), T({ x, y: 1.6, w: 1.0, h: 1.0, fontSize: 60, bold: true, color: C.accent1, fontFace: "Arial" }));
    await badge(s, steps[i][0], x + 1.15, 1.65, 0.95, HEX.dk1, HEX.accent1, steps[i][1]);
    s.addText(steps[i][1], T({ x, y: 2.95, w: 3.7, h: 0.6, fontSize: 22, bold: true, color: C.text1 }));
    s.addText(steps[i][2], T({ x, y: 3.6, w: 3.6, h: 1.8, fontSize: 16, color: C.text2, valign: "top" }));
    if (i < 2) s.addImage({ data: await icon("FaArrowRight", HEX.accent3), x: x + 3.7, y: 1.95, w: 0.35, h: 0.35, objectName: "Arrow " + (i + 1), altText: "" });
  }
  card(s, MX, 5.7, W - 2 * MX, 0.9, HEX.lt2, "Plus checks");
  s.addImage({ data: await icon("FaShieldAlt", HEX.accent2), x: MX + 0.35, y: 5.92, w: 0.45, h: 0.45, objectName: "Shield icon", altText: "" });
  s.addText([{ text: "Bonus: ", options: { bold: true } }, { text: "while reading, it also checks the program for common mistakes before they reach the machine." }],
    T({ x: MX + 1.0, y: 5.7, w: W - 2 * MX - 1.3, h: 0.9, fontSize: 16, color: C.text2, valign: "middle" }));
  s.addNotes("This is the whole idea. Step one, read the program. Step two, simulate how the machine moves, which already beats length divided by speed. Step three, the physics never captures everything, so a small learning model learns the remaining gap from past runs, and the answer comes as a range.");

  // ================================================================ 6 range
  s = content("The idea", "Why a range instead of one number?");
  await badge(s, "FaCloudSunRain", MX, 1.6, 1.0, HEX.lt2, HEX.accent5, "Weather");
  s.addText("Like a weather forecast", T({ x: MX + 1.25, y: 1.6, w: 4.5, h: 1.0, fontSize: 22, bold: true, color: C.text1, valign: "middle" }));
  s.addText("A forecast doesn't say \"it will be 31 °C\". It says \"29 to 33 °C\", and a good forecaster is right about as often as they claim to be.",
    T({ x: MX, y: 2.8, w: 5.4, h: 1.3, fontSize: 16, color: C.text2, valign: "top" }));
  s.addText("How the range is built (conformal prediction)", T({ x: MX, y: 3.95, w: 5.6, h: 0.45, fontSize: 16, bold: true, color: C.text1 }));
  s.addText([
    { text: "Look at how far off the tool was on past jobs", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "Take a miss size that covers 90 % of them", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "Put that margin around the new estimate", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "Check: does the truth land inside 90 % of the time?", options: { bullet: { type: "number" } } },
  ], T({ x: MX, y: 4.45, w: 5.6, h: 1.9, fontSize: 16, color: C.text2, paraSpaceAfter: 6 }));
  // range bar illustration
  card(s, 6.75, 1.6, 5.95, 4.95, HEX.dk1, "Range example");
  s.addText("What the tool says", T({ x: 7.1, y: 1.9, w: 5.2, h: 0.4, fontSize: 14, color: "B9C2CC" }));
  s.addText("Cycle time", T({ x: 7.1, y: 2.45, w: 5.2, h: 0.4, fontSize: 16, color: C.background1 }));
  s.addText("43 min", T({ x: 7.1, y: 2.85, w: 5.2, h: 1.0, fontSize: 54, bold: true, color: C.background1 }));
  s.addText("41 to 46 min  (90 % sure)", T({ x: 7.1, y: 3.85, w: 5.2, h: 0.45, fontSize: 18, color: C.accent1, bold: true }));
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.1, y: 4.75, w: 5.25, h: 0.1, rectRadius: 0.05, fill: { color: "3A4450" }, line: { type: "none" }, objectName: "Bar track" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.9, y: 4.65, w: 2.1, h: 0.3, rectRadius: 0.1, fill: { color: HEX.accent1, transparency: 45 }, line: { type: "none" }, objectName: "Bar range" });
  s.addShape(pres.shapes.RECTANGLE, { x: 9.6, y: 4.5, w: 0.06, h: 0.6, fill: { color: HEX.accent1 }, line: { type: "none" }, objectName: "Bar estimate" });
  s.addShape(pres.shapes.LINE, { x: 7.75, y: 4.5, w: 0, h: 0.6, line: { color: "B9C2CC", width: 1.5, dashType: "dash" }, objectName: "Bar CAM mark" });
  s.addText("CAM says 33 min", T({ x: 7.1, y: 5.2, w: 2.2, h: 0.4, fontSize: 12, color: "B9C2CC" }));
  s.addText("Example figures for illustration", T({ x: 7.1, y: 5.95, w: 5.2, h: 0.35, fontSize: 11, italic: true, color: "8A949E" }));
  s.addNotes("The range is the honest part. The method is called conformal prediction, and the idea is simple: look at how big your past misses were, use a margin that covered 90 percent of them, and then check that the true value really falls inside about 90 percent of the time. The numbers on the right are an illustration, not a real job.");

  // ================================================================ 7 pipeline
  pres.addSection({ title: "How it was built" });
  s = content("How it was built", "Inside the tool");
  const pipe = [
    ["FaFileCode", "Reader", "Turns G-code into moves"],
    ["FaRoute", "Motion planner", "Speed at every corner and curve"],
    ["FaBolt", "Energy model", "Idle + spindle + motion + cutting power"],
    ["FaBrain", "Learned correction", "Small model fixes the leftover gap"],
    ["FaBullseye", "Range", "Margin from past misses"],
    ["FaDesktop", "Web app", "Results on one screen"],
  ];
  const bw = 1.82, gap = 0.2;
  for (let i = 0; i < pipe.length; i++) {
    const x = MX + i * (bw + gap);
    card(s, x, 2.0, bw, 3.0, i >= 3 ? HEX.dk1 : HEX.lt2, "Step " + pipe[i][1]);
    await badge(s, pipe[i][0], x + (bw - 0.8) / 2, 2.25, 0.8, i >= 3 ? HEX.accent1 : HEX.dk1, i >= 3 ? HEX.dk1 : HEX.accent1, pipe[i][1]);
    s.addText(pipe[i][1], T({ x: x + 0.12, y: 3.2, w: bw - 0.24, h: 0.75, fontSize: 16, bold: true, align: "center", valign: "middle", color: i >= 3 ? C.background1 : C.text1 }));
    s.addText(pipe[i][2], T({ x: x + 0.12, y: 3.95, w: bw - 0.24, h: 0.95, fontSize: 13, align: "center", valign: "top", color: i >= 3 ? "D5DCE3" : C.text2 }));
  }
  s.addText("Physics (written by hand)", T({ x: MX, y: 5.25, w: 3 * bw + 2 * gap, h: 0.4, fontSize: 14, bold: true, color: C.accent3, align: "center" }));
  s.addText("Learning + presentation", T({ x: MX + 3 * (bw + gap), y: 5.25, w: 3 * bw + 2 * gap, h: 0.4, fontSize: 14, bold: true, color: C.accent1, align: "center" }));
  s.addText("Separately, a rule checker reads the same moves and flags mistakes. Nothing in the tool ever talks to a real machine: it only reads the program.",
    T({ x: MX, y: 5.95, w: W - 2 * MX, h: 0.7, fontSize: 15, color: C.text2, valign: "middle" }));
  s.addNotes("Left to right is how a program flows through the tool. The first three boxes are physics I wrote by hand. The last three are the learning part and the app. Important for safety: the tool only reads programs, it never sends anything to a machine.");

  // ================================================================ 8 tech
  s = content("How it was built", "What we used");
  const tech = [
    ["FaPython", "Python", "Main language for all the logic"],
    ["FaCalculator", "NumPy", "Fast maths on arrays"],
    ["FaBrain", "scikit-learn", "Learning models (ridge, boosted trees)"],
    ["FaServer", "FastAPI", "Web service the app talks to"],
    ["FaHtml5", "HTML · CSS · JavaScript", "The interface, no framework"],
    ["FaVial", "pytest", "79 automated tests"],
    ["FaCamera", "Playwright", "Drives the app in a browser for testing"],
    ["FaGitAlt", "Git", "Version history, 5 focused commits"],
  ];
  for (let i = 0; i < tech.length; i++) {
    const col = i % 4, row = Math.floor(i / 4);
    const x = MX + col * 3.07, y = 1.6 + row * 1.75;
    card(s, x, y, 2.85, 1.5, HEX.lt2, "Tech " + tech[i][1]);
    await badge(s, tech[i][0], x + 0.25, y + 0.3, 0.85, HEX.dk1, HEX.accent1, tech[i][1]);
    s.addText(tech[i][1], T({ x: x + 1.3, y: y + 0.22, w: 1.45, h: 0.5, fontSize: 16, bold: true, color: C.text1, valign: "middle", fit: "shrink" }));
    s.addText(tech[i][2], T({ x: x + 1.3, y: y + 0.72, w: 1.45, h: 0.65, fontSize: 12, color: C.text2, valign: "top" }));
  }
  card(s, MX, 5.25, W - 2 * MX, 1.35, HEX.dk1, "Research tools");
  await badge(s, "FaSearch", MX + 0.3, 5.47, 0.9, HEX.accent1, HEX.dk1, "Research");
  s.addText([
    { text: "Research:  ", options: { bold: true, color: C.accent1 } },
    { text: "Scopus searches and 42 papers reviewed · open datasets from KIT (Germany) with real machine recordings, for the next stage · AI agents for parallel research and an independent code review", options: { color: C.background1 } },
  ], T({ x: MX + 1.45, y: 5.25, w: W - 2 * MX - 1.8, h: 1.35, fontSize: 15, valign: "middle" }));
  s.addNotes("All free tools, zero budget. Python with NumPy and scikit-learn for the logic and learning, FastAPI for the web service, plain HTML, CSS and JavaScript for the screen. pytest runs 79 tests and Playwright clicks through the app in a real browser. For research I used Scopus through the college login.");

  // ================================================================ 9 app
  pres.addSection({ title: "The product" });
  s = content("The product", "The app: paste a program, get answers");
  s.addImage({ path: path.join(S, "app.png"), x: MX, y: 1.5, w: 8.32, h: 5.2, objectName: "App screenshot", altText: "NC Pre-flight screen: program editor on the left, time and energy ranges, issues and tool path on the right" });
  const callouts = [
    ["FaClock", "Cycle time as a range", "with the simple CAM figure marked for comparison"],
    ["FaBolt", "Energy as a range", "in watt-hours"],
    ["FaExclamationTriangle", "Mistakes to fix", "click one to jump to that line"],
    ["FaChartBar", "Where time goes", "which lines run slower than programmed"],
  ];
  for (let i = 0; i < callouts.length; i++) {
    const y = 1.55 + i * 1.3;
    await badge(s, callouts[i][0], 9.25, y, 0.75, HEX.accent1, "FFFFFF", callouts[i][1]);
    s.addText(callouts[i][1], T({ x: 10.2, y: y - 0.02, w: 2.6, h: 0.45, fontSize: 16, bold: true, color: C.text1 }));
    s.addText(callouts[i][2], T({ x: 10.2, y: y + 0.42, w: 2.6, h: 0.7, fontSize: 13, color: C.text2, valign: "top" }));
  }
  s.addNotes("This is the real app. Left: the program. Right: time and energy as ranges, the issues list, the tool path with slow sections in orange, and a table of where the time goes. The banner at the top always says the calibration is on simulated data, so nobody mistakes it for real-machine accuracy.");

  // ================================================================ 10 mistakes
  s = content("The product", "It also catches mistakes before the machine does");
  s.addImage({ path: path.join(S, "issues.png"), x: MX, y: 1.5, w: 7.2, h: 4.3, objectName: "Issues screenshot", altText: "List of issues found in a faulty program, each with line number, explanation and fix" });
  s.addText("Examples it catches", T({ x: 8.3, y: 1.5, w: 4.4, h: 0.5, fontSize: 20, bold: true, color: C.text1 }));
  const errs = [
    ["FaArrowDown", "Fast move straight into the part"],
    ["FaPowerOff", "Cutting with the spindle switched off"],
    ["FaDrawPolygon", "A curve whose numbers don't add up"],
    ["FaExpandArrowsAlt", "A move past the machine's limits"],
    ["FaTachometerAlt", "Speed above what the machine allows"],
  ];
  for (let i = 0; i < errs.length; i++) {
    const y = 2.15 + i * 0.72;
    await badge(s, errs[i][0], 8.3, y, 0.55, HEX.lt2, HEX.accent4, errs[i][1]);
    s.addText(errs[i][1], T({ x: 9.05, y, w: 3.7, h: 0.55, fontSize: 15, color: C.text2, valign: "middle" }));
  }
  card(s, MX, 6.0, W - 2 * MX, 0.75, HEX.lt2, "Rules note");
  s.addText([{ text: "15 rules + 7 reader warnings.  ", options: { bold: true, color: C.text1 } },
    { text: "Each one says the line, what is wrong and what to do. They are rules, not a full crash simulation.", options: { color: C.text2 } }],
    T({ x: MX + 0.3, y: 6.0, w: W - 2 * MX - 0.6, h: 0.75, fontSize: 15, valign: "middle" }));
  s.addNotes("This is a program I wrote with deliberate mistakes. The tool found the rapid move into the part on line 8, the curve that doesn't close, a move outside the machine's travel, and more. Each issue gives the line, the reason and the fix. These are rules, so they only catch what the rules describe; they don't replace a full simulation.");

  // ================================================================ 11 fair test
  pres.addSection({ title: "Results" });
  s = content("Results", "How we tested it fairly");
  await badge(s, "FaGraduationCap", MX, 1.6, 1.0, HEX.lt2, HEX.dk2, "Exam");
  s.addText("Like a fair exam", T({ x: MX + 1.25, y: 1.6, w: 4.2, h: 1.0, fontSize: 22, bold: true, color: C.text1, valign: "middle" }));
  s.addText("Testing a student on the exact questions they practised proves nothing. So the tool is always tested on a kind of part it has never seen.",
    T({ x: MX, y: 2.8, w: 5.3, h: 1.4, fontSize: 16, color: C.text2, valign: "top" }));
  s.addText([
    { text: "240 generated programs in 6 families", options: { bullet: true, breakLine: true } },
    { text: "Learn from 5 families, test on the hidden 6th", options: { bullet: true, breakLine: true } },
    { text: "Repeat for every family, with 3 different random seeds", options: { bullet: true, breakLine: true } },
    { text: "\"True\" times come from a simulated machine", options: { bullet: true } },
  ], T({ x: MX, y: 4.3, w: 5.4, h: 2.0, fontSize: 15, color: C.text2, paraSpaceAfter: 6 }));
  const fams = [["Pocket", "FaSquare"], ["Contour", "FaRegSquare"], ["Drilling", "FaDotCircle"], ["3D surface", "FaWater"], ["Trochoid", "FaCircleNotch"], ["Engraving", "FaSignature"]];
  for (let i = 0; i < 6; i++) {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 6.65 + col * 2.05, y = 1.65 + row * 2.2;
    const hidden = i === 2;
    card(s, x, y, 1.85, 1.95, hidden ? HEX.accent1 : HEX.lt2, "Family " + fams[i][0]);
    s.addImage({ data: await icon(fams[i][1], hidden ? "FFFFFF" : HEX.dk2), x: x + 0.6, y: y + 0.3, w: 0.65, h: 0.65, objectName: fams[i][0] + " icon", altText: "" });
    s.addText(fams[i][0], T({ x: x + 0.1, y: y + 1.05, w: 1.65, h: 0.4, fontSize: 15, bold: true, align: "center", color: hidden ? C.background1 : C.text1 }));
    s.addText(hidden ? "HIDDEN: test" : "learn", T({ x: x + 0.1, y: y + 1.45, w: 1.65, h: 0.35, fontSize: 12, align: "center", bold: hidden, color: hidden ? C.background1 : C.accent3 }));
  }
  s.addText("Round 3 of 6 shown: drilling is held out", T({ x: 6.65, y: 6.15, w: 6.0, h: 0.4, fontSize: 12, italic: true, color: C.accent3, align: "center" }));
  s.addNotes("This is the part I'm proudest of. If you test on random jobs, the test jobs look like the training jobs and everything looks great. Instead I hide a whole family of parts, for example all drilling programs, train on the rest, and test on the hidden one. Then I rotate through all six. The catch: all of this is on a simulated machine, which I'll come back to.");

  // ================================================================ 12 results
  s = content("Results", "What we found (on a simulated machine)");
  SIM(s, MX, 1.35);
  s.addChart(pres.charts.BAR, [{ name: "Time error", labels: ["Length ÷ speed", "Physics only", "Physics + learning"], values: [22.0, 17.8, 6.6] }], {
    x: MX, y: 1.75, w: 5.9, h: 4.15, barDir: "col", objectName: "Time error chart",
    chartColors: [HEX.accent3, HEX.accent3, HEX.accent1], invertedColors: [HEX.accent3, HEX.accent3, HEX.accent1],
    showTitle: true, title: "Average time error on unseen parts (%)", titleFontSize: 14, titleColor: HEX.dk2, titleFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 14, dataLabelColor: HEX.dk2, dataLabelFontFace: "+mn-lt", dataLabelFormatCode: "0.0",
    showLegend: false, valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 26,
    catAxisLabelColor: "5B6670", catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt",
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, barGapWidthPct: 60,
  });
  s.addChart(pres.charts.BAR, [
    { name: "Time", labels: ["Standard ranges", "Plain ±10 %", "Our ranges"], values: [67.2, 87.9, 86.2] },
    { name: "Energy", labels: ["Standard ranges", "Plain ±10 %", "Our ranges"], values: [81.1, 76.0, 86.4] },
  ], {
    x: 6.85, y: 1.75, w: 5.9, h: 4.15, barDir: "col", objectName: "Coverage chart",
    chartColors: [HEX.dk2, HEX.accent1],
    showTitle: true, title: "How often the truth fell inside a 90 % range (%)", titleFontSize: 14, titleColor: HEX.dk2, titleFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 12, dataLabelColor: HEX.dk2, dataLabelFontFace: "+mn-lt", dataLabelFormatCode: "0",
    showLegend: true, legendPos: "b", legendFontSize: 12, legendFontFace: "+mn-lt", legendColor: HEX.dk2,
    valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 100,
    catAxisLabelColor: "5B6670", catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt",
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, barGapWidthPct: 50,
  });
  card(s, MX, 6.05, W - 2 * MX, 0.8, HEX.lt2, "Takeaway");
  s.addText([{ text: "Takeaway:  ", options: { bold: true, color: C.accent1 } },
    { text: "error dropped from 22 % to 7 %. Our ranges were the most consistent, but still a little short of 90 %.", options: { color: C.text1 } }],
    T({ x: MX + 0.3, y: 6.05, w: W - 2 * MX - 0.6, h: 0.8, fontSize: 16, valign: "middle" }));
  s.addNotes("Left: time error on parts the model hadn't seen. Length divided by speed is off by 22 percent on average, the physics planner 18, physics plus learning about 7. Right: how often the true value landed inside a range that claims 90 percent. The standard way of building ranges managed only 67 percent for time. A plain plus-or-minus 10 percent did well on time but badly on energy. Ours was the most consistent across both, around 86 percent, still a little short of 90. Also: when the tool says a program looks familiar, coverage was 94 to 98 percent. All simulated.");

  // ================================================================ 13 limits
  s = content("Results", "Honest limits");
  const lims = [
    ["FaFlask", "Simulated machine only", "The \"true\" times come from a simulator that shares code with the tool. Real accuracy is still unknown."],
    ["FaBullseye", "Ranges a bit too narrow", "About 86 % coverage against a 90 % target on new kinds of parts."],
    ["FaExchangeAlt", "A second machine isn't solved", "A simple correction from a few runs did not make the ranges reliable on another machine."],
    ["FaCube", "3-axis milling only", "No 5-axis, no lathes. Drilling cycles and cutter compensation are flagged, not simulated."],
  ];
  for (let i = 0; i < 4; i++) {
    const col = i % 2, row = Math.floor(i / 2);
    const x = MX + col * 6.15, y = 1.65 + row * 2.45;
    card(s, x, y, 5.9, 2.15, HEX.lt2, "Limit " + (i + 1));
    await badge(s, lims[i][0], x + 0.35, y + 0.4, 0.95, HEX.dk1, HEX.accent1, lims[i][1]);
    s.addText(lims[i][1], T({ x: x + 1.6, y: y + 0.3, w: 4.0, h: 0.55, fontSize: 19, bold: true, color: C.text1, valign: "middle" }));
    s.addText(lims[i][2], T({ x: x + 1.6, y: y + 0.88, w: 4.05, h: 1.1, fontSize: 15, color: C.text2, valign: "top" }));
  }
  s.addText("Status: working prototype. Not yet proven on real machines.", T({ x: MX, y: 6.55, w: W - 2 * MX, h: 0.45, fontSize: 16, bold: true, color: C.accent4 }));
  s.addNotes("I want to be upfront about what this is not. Every number came from a simulated machine. The ranges are slightly too narrow. Moving to a second machine isn't solved. And it only handles 3-axis milling. So it's a working prototype, not a proven product.");

  // ================================================================ 14 next
  pres.addSection({ title: "Next steps" });
  s = content("Next steps", "What comes next");
  const next = [
    ["FaDatabase", "Real machine data", "Run the same tests on open recordings from 2 real machines at KIT, Germany (87 jobs)."],
    ["FaSlidersH", "Fix the second machine", "Re-learn the range margin from a few runs on the new machine."],
    ["FaHandshake", "Pilot with a local shop", "Read-only logging on one machine, with the shop's permission."],
    ["FaFileAlt", "Write it up", "A paper, if the real-data results hold."],
  ];
  s.addShape(pres.shapes.LINE, { x: MX + 0.6, y: 2.45, w: W - 2 * MX - 1.2, h: 0, line: { color: HEX.lt2, width: 4 }, objectName: "Timeline" });
  for (let i = 0; i < 4; i++) {
    const x = MX + i * 3.08;
    await badge(s, next[i][0], x + 0.85, 1.85, 1.2, i === 0 ? HEX.accent1 : HEX.dk1, i === 0 ? HEX.dk1 : HEX.accent1, next[i][1]);
    s.addText("Step " + (i + 1), T({ x, y: 3.3, w: 2.9, h: 0.4, fontSize: 13, bold: true, color: C.accent3, align: "center" }));
    s.addText(next[i][1], T({ x, y: 3.7, w: 2.9, h: 0.6, fontSize: 19, bold: true, color: C.text1, align: "center" }));
    s.addText(next[i][2], T({ x: x + 0.1, y: 4.35, w: 2.7, h: 1.5, fontSize: 15, color: C.text2, valign: "top" }));
  }
  card(s, MX, 6.0, W - 2 * MX, 0.8, HEX.lt2, "Need");
  s.addText([{ text: "Needed for step 1:  ", options: { bold: true, color: C.text1 } }, { text: "about 50 GB of disk space to download the first dataset.", options: { color: C.text2 } }],
    T({ x: MX + 0.3, y: 6.0, w: W - 2 * MX - 0.6, h: 0.8, fontSize: 16, valign: "middle" }));
  s.addNotes("The obvious next step is real data. A research group at KIT in Germany published recordings from two real machines including the exact programs they ran. Running the same fair test on that tells us whether any of this holds up. After that, fix the second-machine problem, try it read-only in a local shop, and write it up if the results are good.");

  // ================================================================ 15 close
  s = pres.addSlide({ masterName: "Closing", sectionTitle: "Next steps" });
  s.addText("Know before you cut", { placeholder: "title" });
  s.addText("Thank you · Questions?", { placeholder: "body" });
  s.addImage({ data: await icon("FaCog", HEX.accent1), x: (W - 0.9) / 2, y: 1.2, w: 0.9, h: 0.9, objectName: "Gear icon", altText: "" });
  s.addNotes("To sum up: read the program, simulate the motion, learn the gap, and give an honest range, tested fairly on parts it has never seen. Thank you.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
