# GT Dataset v2 - Reference ↔ GT Verification Document

> **Dataset Version**: 2.0
> **Created**: 2026-02-11
> **Purpose**: IEEE CASE 2026 논문 제출용 GT 데이터셋 검증
> **Principle**: 모든 GT 공정 스텝은 접근 가능한 HTML 레퍼런스 원문에서 직접 추출

---

## Summary

| Product | Steps | Reference Type | URL Accessible | Coverage |
|---------|-------|---------------|----------------|----------|
| P01 EV Battery | 14 | HTML (batterydesign.net) | ✅ | 14/14 |
| P02 BIW | 9 | HTML (Toyota Global) | ✅ | 9/9 |
| P03 SMT | 7 | HTML (PCBOnline) | ✅ | 7/7 |
| P04 Semiconductor | 9 | HTML (Rapidus) | ✅ | 9/9 |
| P05 Solar PV | 9 | HTML (Sinovoltaics) | ✅ | 9/9 |
| P06 Hairpin Motor | 8 | HTML (grwinding/laserax) | ✅ | 8/8 |
| P07 OLED | 6 | HTML (Canon Tokki) | ✅ | 6/6 |
| P08 Washing Machine | 8 | HTML (MadeHow) | ✅ | 8/8 |
| P09 Pharma Tablet | 6 | HTML (Pharmaguideline/CRB) | ✅ | 6/6 |
| P10 Tire | 7 | HTML (Nexen Tire) | ✅ | 7/7 |

**Total: 83 steps across 10 products, all verified against accessible HTML sources.**

---

## P01. EV Battery Cell (EV 배터리 셀)

**Reference**: https://www.batterydesign.net/manufacture/cell-manufacturing/battery-cell-manufacturing-process/
**Sub-pages**: electrode-manufacturing/, cell-assembly/, formation-aging/, cell-final-assembly-and-finishing/

### Phase 1: Electrode Manufacturing

| # | GT Step | Reference Quote |
|---|---------|----------------|
| 1 | Mixing | "The anode and cathode materials are mixed just prior to being delivered to the coating machine." |
| 2 | Coating | "The anode and cathodes are coated separately in a continuous coating process." The cathode is coated onto aluminium, polymer binder adheres the coatings to copper and aluminium electrodes. |
| 3 | Drying | "Immediately after coating the electrodes are dried. This is done with convective air dryers on a continuous process." Solvents are recovered. |
| 4 | Calendering | "This is a rolling of the electrodes to a controlled thickness and porosity." Rollers compress the active layer to the target dimension. |

### Phase 2: Cell Assembly

| # | GT Step | Reference Quote |
|---|---------|----------------|
| 5 | Slitting | Cuts electrodes lengthwise to the required width for the cell. Clean edges without burrs are critical. |
| 6 | Final Drying | "The electrodes are dried again to remove all solvent content and to reduce free water ppm prior to the final processes before assembling the cell." |
| 7 | Cutting | "Final shape of the electrode including tabs for the electrodes are cut." |
| 8 | Winding/Stacking | "In a cylindrical cell the anode, cathode and separator are wound into a spiral." For pouch cells, electrodes are stacked in alternating layers. |
| 9 | Terminal Welding | "The anodes are connected to the negative terminal and the cathodes to the positive terminal." |
| 10 | Canning (Enclosing) | "The electrodes either as a roll or pack of stacked layers are loaded into the can or pouch." |

### Phase 3: Cell Finishing

| # | GT Step | Reference Quote |
|---|---------|----------------|
| 11 | Electrolyte Filling | "The up until now dry cell is now filled with electrolyte. A partial vacuum is created in the cell and a pre-determined quantity of electrolyte is delivered to the cell." The vacuum aids wetting of all layers. |
| 12 | Formation & Sealing | "The cell is charged and at this point gases form in the cell. The gases are released before the cell is finally sealed." This is when the SEI layer forms on the anode. |
| 13 | Ageing | "The cells are stored at a controlled temperature for a period of time. This allows the SEI to stabilize." Duration ranges from 3 days to 3 weeks. |
| 14 | Final Control Checks | "All data is recorded against the cells unique identification." Checks include delta OCV rate, mass, dimensions, leak checks, thickness, and visual inspection. |

---

## P02. Automotive BIW (자동차 차체)

**Reference 1**: https://global.toyota/en/company/plant-tours/stamping/
**Reference 2**: https://global.toyota/en/company/plant-tours/welding/

### Stamping Process (from Ref 1)

| # | GT Step | Reference Quote |
|---|---------|----------------|
| 1 | Steel Plate Preparing | Steel plates of varying hardness are selected and readied. More than a dozen steel plate types are used per car. |
| 2 | Coil Carrying & Stretching | Steel coils are transported and unrolled. One coil measures approximately 2.5 km and produces roughly 300 vehicles. |
| 3 | Punching (Blanking) | Openings are cut where doors will be attached; excess material is removed simultaneously. |
| 4 | Stamping (Drawing) | Core forming operation in 4 sub-steps, each lasting 3 seconds at 1,600 tons of pressure. Dies achieve precision to a 1/1000 mm threshold. |
| 5 | Part Arranging | Pressed parts are rearranged in the order they will be used for the welding process. |

### Welding/Body Assembly Process (from Ref 2)

| # | GT Step | Reference Quote |
|---|---------|----------------|
| 6 | Body Assembly (Welding) | Floor, sides, and ceiling are joined together with welding at approximately 4,000 locations. |
| 7 | Reinforcement Welding | Specialized robots weld more than 500 additional locations to strengthen the body. |
| 8 | Door/Hood/Trunk Attachment | Doors, hood, and trunk lid are affixed. Doors are intentionally displaced because subsequent component weight lowers them back into alignment. |
| 9 | Body Inspection | Quality verification using the principle of Jikotei-kanketsu (self-completion) to prevent defect propagation. |

---

## P03. Smartphone SMT (스마트폰 SMT)

**Reference**: https://www.pcbonline.com/blog/smt-manufacturing-process.html

| # | GT Step | Reference Quote |
|---|---------|----------------|
| 1 | PCB Loading | "The loader automatically sends the bare PCB one by one through a transmission rod into a solder paste printing machine." |
| 2 | Solder Paste Printing | "A scraper presses the solder paste through the stencil holes to 'print' on the PCB." |
| 3 | SPI (Solder Paste Inspection) | "The PCB passes the infrared cameras of the SPI machine, which records hundreds of images in seconds and compares them with the reference." |
| 4 | Pick and Place (Mounting) | "Robot arms in the machines place them at the expected positions, where the suction nozzle will come over to pick them up and place them onto the PCB." |
| 5 | Reflow Soldering | "The PCB is sent into the reflow oven...The process includes preheating, baking until the solder paste and PCB pads form the intermetallic compound, and cooling down." |
| 6 | AOI (Optical Inspection) | "The PCBAs pass the AOI machines' infrared cameras one by one, and all the surface details are scanned and analyzed by the computer." |
| 7 | AXI (X-ray Inspection) | "It is necessary to scan the hidden solder balls beneath the BGA with an X-ray...to ensure the solder balls have no breaks, pinholes, or other defects." |

**Note**: FAI (First Article Inspection) exists in reference but is described as prototyping-only, excluded from production GT.

---

## P04. Semiconductor Backend Packaging (반도체 후공정)

**Reference**: https://www.rapidus.inc/en/tech/te0010/

| # | GT Step | Reference Quote |
|---|---------|----------------|
| 1 | Bump Formation | "Bumps -- microscopic protruding connection terminals -- are formed on each chip's electrode pads at the wafer level." |
| 2 | Wafer Dicing | "The silicon wafer is precisely cut and divided into individual chips, also called dies." |
| 3 | Flip-Chip Bonding | "Each chip is rotated 180 degrees, aligned to the substrate's connection pads and bonded." |
| 4 | Underfill Dispensing | "Underfill is dispensed and drawn by capillary action into the narrow gap between the chip and substrate." |
| 5 | Molding (Encapsulation) | "The entire assembly is encapsulated with resin using specialized molding equipment." |
| 6 | Burn-in Testing | "Devices are powered at elevated temperature and voltage to accelerate the detection and removal of early failures." |
| 7 | Reliability Testing | "Environmental stresses such as temperature cycling and high-temperature/high-humidity bias is applied to evaluate stability." |
| 8 | Electrical Characteristic Testing | "Operating voltage and signal characteristics are measured at room and high temperatures to verify specification compliance." |
| 9 | Visual Inspection & Laser Marking | Only passing devices receive "laser marking and are shipped as finished devices." |

**Note**: v1 had single "Final Testing" step; v2 separates into Burn-in/Reliability/Electrical per reference granularity.

---

## P05. Solar PV Module Assembly (태양광 PV 모듈)

**Reference**: https://sinovoltaics.com/learning-center/manufacturing/solar-panel-manufacturing-process-from-cell-to-module/

| # | GT Step | Reference Quote |
|---|---------|----------------|
| 1 | Cell Sorting/Testing | "Cells are sorted into bins based on their electrical characteristics -- mixing cells with different current ratings in the same string creates mismatch losses that reduce overall module output." |
| 2 | Tabbing and Stringing | "The process of contacting the solar cell busbars using tinned copper ribbons is called tabbing, and connecting the solar cells in a series of 6-12 in numbers is called stringing." |
| 3 | Layup | "Strings are placed on top of a glass sheet with a layer of EVA and the strings are interconnected. Another layer of EVA is put on top of the interconnected strings and a backsheet (typically tedlar) is placed on top." |
| 4 | Lamination | "The stack enters the laminator, where vacuum, heat, and pressure transform the separate layers into a single cohesive unit. The lamination cycle typically runs 8-15 minutes at temperatures around 140-150°C." |
| 5 | EL Testing | "EL testing catches any damage that occurred during assembly." "Electroluminescence technology enables identification of defects invisible otherwise, including cell damage and microcracks." |
| 6 | Framing | "After lamination, modules go through trimming (removing excess encapsulant and back sheet), framing (attaching aluminum frames with silicone)." |
| 7 | Junction Box Installation | "A junction box is attached to the rear of the module. The module's electrical cables are attached to the copper ribbons, which pass into the junction box through holes in the rear glass." |
| 8 | IV Flash Test | "The testing included a flash test that measures the open-circuit voltage (VOC), voltage at maximum power point (VMP), short-circuit current (ISC)." |
| 9 | Final Inspection & Packaging | "After passing quality tests, each module undergoes cleaning and final visual inspection before packaging." |

**Canonical flow (Sinovoltaics)**: "stringer, lay up, lamination, EL test, frame, junction box assembly, cleaning, IV test, final inspection, and packaging."

---

## P06. EV Motor - Hairpin Stator (전기차 모터)

**Reference 1**: https://www.grwinding.com/hairpin-electric-motor/
**Reference 2**: https://www.laserax.com/blog/hairpin-motor

| # | GT Step | Reference Quote | Source |
|---|---------|----------------|--------|
| 1 | Wire Straightening & Cutting | "The process starts by straightening enameled copper bars to remove any curvature, then cutting them to the exact length needed for each hairpin segment." | grwinding |
| 2 | Hairpin Forming (Bending) | "The straight copper pieces are bent into precise U-shapes using CNC bending machines—this is where they get the name 'hairpins.'" | grwinding |
| 3 | Slot Insulation Paper Insertion | "The insulation paper placed in the stator slots to prevent abrasion between hairpins and the steel laminations" | laserax |
| 4 | Hairpin Insertion | "These hairpins are carefully inserted into the stator slots, guided by automated systems to ensure high precision." | grwinding |
| 5 | Laser Insulation Stripping | "The insulation at the hairpin ends is stripped using lasers, which offer cleaner, more accurate results than mechanical methods—crucial for reliable welding." | grwinding |
| 6 | End Twisting | "The hairpin ends are twisted..." (prior to welding to form continuous electrical circuits) | grwinding |
| 7 | Laser Welding | "...and laser welded to form continuous electrical circuits with minimal resistance and consistent geometry." | grwinding |
| 8 | Impregnation (Epoxy Coating) | "The welded areas are insulated with epoxy resin through dipping or powder coating, protecting the motor from heat, moisture, and electrical faults." | grwinding |

---

## P07. OLED Display Panel (OLED 디스플레이)

**Reference**: https://tokki.canon/eng/organic_el/process.html

Canon Tokki defines the OLED mass production process in three phases:

> "The mass production process is divided into three steps: 'pre-process' that primarily makes TFT circuits, 'vapor deposition process' that mainly deposits organic material, and 'post-process' that consists of sealing, cutting, and wiring connections."

| # | GT Step | Phase | Reference Quote |
|---|---------|-------|----------------|
| 1 | Substrate Preparation | Pre-process | ITO surface must be cleaned thoroughly. Typical surface pretreatment methods include chemical (acid-base treatment) and physical (O2 plasma treatment, inert gas sputtering). |
| 2 | TFT Backplane Formation | Pre-process | "In the TFT process, a TFT circuit is formed to regulate the current for each pixel." |
| 3 | Organic Layer Deposition (VTE) | Vapor Deposition | "An evaporation source (a crucible) is packed with an organic material and heated to approximately 300°C, and the material is evaporated. Evaporated particles travel in a straight line and adhere to the glass substrate." A vapor deposition mask with holes deposits R/G/B in the desired position. |
| 4 | Encapsulation | Post-process | "The encapsulation layer is strictly required to protect the nanometer-thin OLED layers from mechanical damages, and also because of the sensitivity of the used materials to oxygen and moisture." |
| 5 | Panel Cutting | Post-process | "The post-process consists of sealing, cutting, and wiring connections." Multiple displays made on mother substrate are cut into individual panels. |
| 6 | Module Assembly (Wiring/Bonding) | Post-process | Wiring connections are made in the post-process to integrate the panel with driver ICs and FPCs. |

---

## P08. Domestic Washing Machine (가정용 세탁기)

**Reference**: https://www.madehow.com/Volume-1/Washing-Machine.html

### Phase 1: Fabrication

| # | GT Step | Reference Quote |
|---|---------|----------------|
| 1 | Sheet Metal Pressing/Stamping | "Most sheet metal parts are formed by a machine called a press...presses a piece of sheet metal between two halves of a mold called a die." |
| 2 | Plastic Injection Molding | "After being heated to its melting point, the plastic is forced into the mold under high pressure. Next, water is passed through the mold to cool and solidify the part." |
| 3 | Tub/Drum Manufacturing | "After being rolled into a drum shape, the side is welded...drum is placed on an expander, which stretches the tub into its final shape. A bottom is then welded onto the drum." |
| 4 | Painting (Powder Coating) | Electrically-charged powder paint sprayed onto parts, then conveyed into an oven that melts the paint for a durable finish. |

### Phase 2: Sub-assembly

| # | GT Step | Reference Quote |
|---|---------|----------------|
| 5 | Sub-assembly (Transmission/Pump) | **Transmission**: "Workers bolt, snap, or press several shafts and gears together. Workers then add a metered amount of oil and bolt the unit together." **Pump**: "Robots place the impeller and seals in the cover and body, and seal the pump." |

### Phase 3: Final Assembly

| # | GT Step | Reference Quote |
|---|---------|----------------|
| 6 | Motor/Pump Installation | "Pump and mounting bracket are now bolted onto the motor, which is then fitted with a shield to protect against potential leaks...bolted to the base...connected with a belt and hoses." |
| 7 | Final Assembly | Cabinet and controls: Lid hinges attached, control panel mounted with graphics, wiring harness connected, cabinet positioned by robot. "Cabinet is bolted to the base, and the controls are snapped together with the mating connectors." |
| 8 | Leak/Function Testing | All components tested for operation, leaks, noise, and vibration before and after final assembly. |

---

## P09. Continuous Pharmaceutical Tablet Manufacturing (연속식 제약 정제)

**Reference 1**: https://www.pharmaguideline.com/2023/03/different-stages-of-tablet-manufacturing.html
**Reference 2**: https://www.crbgroup.com/insights/pharmaceuticals/oral-solid-dosage-manufacturing

| # | GT Step | Reference Quote | Source |
|---|---------|----------------|--------|
| 1 | Feeding | "Continuous feeding of formulation components is most often accomplished through Loss-In-Weight (LIW) feeders, with each feeder running at a specified feed rate defined by formulation." | Tandfonline / GEA |
| 2 | Blending/Mixing | "Blending helps to make a homogeneous mixture where active material mixes well throughout the excipients." "Blending plays an important role in tablet manufacturing because it ensures the even distribution of active ingredients." | Pharmaguideline |
| 3 | Granulation | "Granulation is the most important step of tablet manufacturing. Granulation is the process of changing powder into granules. Granulation improves the flow of the material which makes the compression process easy." | Pharmaguideline |
| 4 | Drying | "Granules are dried to remove the excess moisture and solvents used in the granulation process. In pharmaceutical manufacturing fluid bed dryers are widely used." | Pharmaguideline |
| 5 | Compression (Tableting) | "Compression is the process of tablet making. Here granules are compressed into tablets of desired shape and size." | Pharmaguideline |
| 6 | Coating | "The coating is the outermost smooth layer of a tablet. It gives advantages including improved appearance and stability, reduced dissolution rate and masks unpleasant taste." | Pharmaguideline |

**Continuous manufacturing context (CRB Group)**: "A fully integrated CM system begins at bulk powder handling and ends at tablet coating, with full integration and process control from 'powders in' to final dose form coated 'tablets out.'"

---

## P10. Tire Manufacturing (타이어 제조)

**Reference**: https://www.nexentire.com/international/information/tire_information/basic_sense/process.php

| # | GT Step | Reference Quote |
|---|---------|----------------|
| 1 | Mixing | "Adding and mixing various chemicals to crude rubber according to the characteristics and intended use of each tire." |
| 2 | Extrusion | "Rubber is then created into a certain regular width and thickness" to form treads and sidewalls. |
| 3 | Calendering | "Evenly applying and thinly topping a certain thickness of rubber sheets" on steel and fabric cords so tires maintain form under vehicle weight. |
| 4 | Bead Processing | "Coating steel wires with rubber multiple times in a certain thickness, and attaching filler rubber" to fix the tire to wheel rims. |
| 5 | Building | "Cylindrical green tires are made by consecutively attaching all components" including carcass, beads, sidewalls, belts, and treads. |
| 6 | Curing | "Adding heat and pressure inside and outside" using a mold to create the tread design, elasticity, and final structure. |
| 7 | Testing & Shipping | Five quality tests: visual inspection, weight distribution analysis, dynamic balance testing, uniformity assessment, and x-ray verification before classification and shipment. |

---

## v1 → v2 Changes Summary

| Product | v1 Steps | v2 Steps | Change Description |
|---------|----------|----------|-------------------|
| P01 | 11 | 14 | PDF→HTML. Added Final Drying, Cutting, Ageing, Final Control Checks per batterydesign.net |
| P02 | 8 | 9 | PDF→HTML. Toyota plant tour pages (Stamping+Welding). Added Inspection step |
| P03 | 7 | 7 | Kept. Same reference, all steps verified |
| P04 | 7 | 9 | Kept reference. Testing expanded to 3 sub-steps per Rapidus detail |
| P05 | 8 | 9 | Scribd PDF→Sinovoltaics HTML. Added EL Testing; removed Laser Cutting (not in new ref) |
| P06 | 9 | 8 | ResearchGate 403→grwinding+laserax HTML. Skinning→Laser Stripping; combined Straightening+Cutting |
| P07 | 7 | 6 | UBI PDF→Canon Tokki HTML. Simplified to match 3-phase reference description |
| P08 | 6 | 8 | Scribd PDF→MadeHow HTML. Added Injection Molding, Painting, Sub-assembly steps |
| P09 | 6 | 6 | CCPMJ PDF→Pharmaguideline+CRB HTML. Same 6 steps, better source traceability |
| P10 | 6 | 7 | Kept reference. Extrusion/Calendering split into 2 per Nexen description |
