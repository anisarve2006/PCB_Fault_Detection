# PCB Defect Detection with Computer Vision: Analysis, Architectures and Project Plan

Oct 10, 2026 · @Pushkar

## Executive summary

Start with a YOLO26 detector trained on a board-level split, challenge it with RF-DETR, add tiled inference for full-board images, and treat an anomaly-detection branch as the production-grade extension. This report compares six architectures for finding six PCB defect types, with the reasons, evidence and risks for each.

- **The dataset** is listed on Kaggle as 10,666 images, six defect classes, YOLO labels. It is PKU-Market-PCB, whose defects were drawn in Photoshop; the cropped version has balanced classes but a leakage risk and a synthetic-to-real gap (Section 2).
- **The biggest threat to your results is the split,** not the model. Many crops come from the same 693 boards, so split by board and report mAP@50–95 and per-class recall, because mAP@50 is already near 99% for ordinary models (Section 3).
- **Six architectures,** each with a reason to exist: A single-stage YOLO26, B transformer detectors, C tiled inference, D SAM-based segmentation, E anomaly detection, F a hybrid with a reference image (Sections 4 to 10).
- **Latest tools used:** YOLO26 (January 2026), RF-DETR, DEIMv2, RT-DETRv4, SAM 3, Anomalib with Dinomaly, SAHI and its 2026 adaptive variant, and the June 2026 RefDiffNet reference-difference module (Section 12).
- **Plan:** five phases with gates, where Phase 1 alone is a complete project (Section 14).

What I could not verify: image size, licence terms and whether the provided splits leak; any numbers on this exact Kaggle copy. All accuracy figures quoted come from papers and vendor documentation on related data, and the latency figures in Sections 6 and 13 are my estimates.

## 1. Problem context

The task is automated optical inspection (AOI) of bare printed circuit boards: find each manufacturing defect in a board image, say what type it is, and say where it is. The six defect classes in this dataset are the standard ones in PCB research ([Huang and Wei, PKU dataset paper](https://arxiv.org/abs/1901.08204)):

| Defect | What it is | Why it matters |
| --- | --- | --- |
| Missing hole | A drill hole that is blocked or was never drilled | Components cannot be mounted |
| Mouse bite | Small nicks along a trace or board edge | Weakens the trace, can break over time |
| Open circuit | A break in a conductive trace | Direct functional failure |
| Short | Two traces that should be separate are joined | Direct functional failure |
| Spur | A thin protrusion off a trace | Leakage and short-circuit risk |
| Spurious copper | Stray copper dots or patches | Short-circuit risk |

Descriptions follow the [SME-YOLO paper](https://arxiv.org/pdf/2601.11402).

Four properties of this problem decide which architecture is sensible:

1. **Defects are tiny relative to the board.** On the original PKU boards, average defect area is about 2,700 to 7,300 pixels on images of roughly 2777 × 2138 pixels, which is 0.05% to 0.13% of the image ([SME-YOLO](https://arxiv.org/pdf/2601.11402)).
2. **Defects look like the background.** A short or open circuit differs from a healthy trace by a few pixels of geometry, not by colour or texture.
3. **Misses and false alarms cost differently.** A missed short ships a dead board; a false alarm costs a second look by a human. Recall matters more than precision, within a review budget.
4. **Real factories rarely have many labelled defects.** Good boards are plentiful and defects are rare, which is why anomaly detection (Architecture E) belongs in the comparison even though this dataset is labelled.

## 2. Dataset analysis

The [Kaggle dataset](https://www.kaggle.com/datasets/fedybenhassouna/printed-circuit-board-pcb-defects) is listed as 10,666 images with six defect types in YOLO annotation format. The dataset description you shared confirms the source: the PKU-Market-PCB dataset from Peking University's Open Lab on Human Robot Interaction, downloaded from the Tiny-Defect-Detection-for-PCB GitHub repository. That description still says 1,386 images, so it was copied from the original boards, while the 10,666 files are cropped images. The folders are train, val and test, with a data.yaml listing six classes (0 mouse\_bite, 1 spur, 2 missing\_hole, 3 short, 4 open\_circuit, 5 spurious\_copper). Image size and the licence terms are still unconfirmed: the card says only "Other" and the description gives no terms.

**Crop lineage (my inference).** The counts match the augmented version of the Peking University PKU-Market-PCB dataset: 10,668 images and 21,664 labelled objects, made by cutting 693 original defective boards into 600 × 600 crops ([DatasetNinja](https://datasetninja.com/augmented-pcb-defect), [ESRPCB paper](https://arxiv.org/pdf/2506.13476)). The two-image difference means the Kaggle author may have filtered or re-exported it.

If that lineage holds, the class balance is excellent:

| Class | Images (augmented set) | Labelled objects | Average defect area on original boards (px²) |
| --- | --- | --- | --- |
| Missing hole | 1,832 | 3,612 | 4,620 |
| Mouse bite | 1,852 | 3,684 | 3,896 |
| Open circuit | 1,740 | 3,548 | 2,675 |
| Short | 1,732 | 3,508 | 7,327 |
| Spur | 1,752 | 3,636 | 5,048 |
| Spurious copper | 1,760 | 3,676 | 5,427 |

Counts from [ESRPCB](https://arxiv.org/pdf/2506.13476); areas from [SME-YOLO](https://arxiv.org/pdf/2601.11402).

**What this means for the project**

- **Class imbalance is not the problem.** Each class has about 3,500 to 3,700 objects, so you do not need class re-weighting or focal-loss tricks for balance.
- **The crops already solve most of the resolution problem.** A 4,000 px² defect is roughly 63 × 63 pixels, which fits a 640 px input without downscaling. The hard cases are thin, low-area defects (open circuit, spur), where the box is small and elongated. That is my calculation from the published areas.
- **Data leakage is the biggest risk.** Many crops come from the same 693 boards. A random image-level split puts neighbouring crops of one board in both train and test, and inflates every score. Split by source board, or recover the board ID from filenames if they carry one.
- **The images are synthetic.** The original PKU boards were made by editing defect-free images, with 3 to 5 defects per board ([PKU paper](https://arxiv.org/abs/1901.08204)). Expect a model that scores very high here and drops on photographs of real boards, with different lighting, camera and copper finish.
- **Template images may be missing.** The original dataset provides a defect-free reference per board for reference-comparison methods. The Kaggle copy may not include them, which affects Architecture F.
- **The benchmark is nearly saturated at mAP@50.** Published YOLO variants report mAP@50 from the mid-90s up to 99%, but mAP@50–95 sits around 60 to 66% ([YOLOv9 PCB study](https://www.sciopen.com/article/10.32604/cmc.2026.080112), [DRM-YOLOv8n](https://m.researching.cn/articles/OJ582a9cfa29f8a2ba)). Protocols differ between papers, so treat these as ranges, not a leaderboard. Report mAP@50–95 and per-class recall to show real differences.

* **The defects were drawn in Photoshop.** The dataset description says so. Editing can leave traces, such as sharpness or compression differences around a defect, and a model can learn those traces instead of how real defects look. Test with re-compressed and lightly blurred images, and on the real boards of the Mendeley set.
* **The train, val and test folders are provided and probably random at crop level.** Crops of the same board may sit in different folders, which inflates scores. Run a near-duplicate check across the folders before trusting any number; the leakage script delivered with this update does that.
* **The original template images are probably not in this copy.** The folders shown are only train, val and test. The PKU paper describes template and test pairs from 10 standard boards, so check the GitHub source for templates, which the anomaly and reference-difference architectures need.
* **The licence needs checking.** The card says "Other", so read the PKU terms before any commercial use. This is separate from the Ultralytics AGPL question.

Two other public sets are useful as out-of-distribution tests: [DeepPCB](https://arxiv.org/abs/1902.06197), with 1,500 aligned template and tested image pairs at 640 × 640, and the 2025 [Mendeley PCB-Defect set](https://data.mendeley.com/datasets/vdj74sngvn/1) of 230 real etched boards (1,704 boxes, COCO JSON). DeepPCB's defect list differs slightly: it includes pin hole instead of missing hole ([RefDiffNet](https://arxiv.org/abs/2606.00852)), so map classes carefully.

## 3. Evaluation protocol and success criteria

Report mAP@50–95 and per-class recall, not mAP@50 alone, and split the data by source board. mAP@50 is already 94 to 99% for ordinary YOLO models on PKU-style data, so it cannot separate good from great (Section 2).

**Split rules**

- Split by source board: train 80%, validation 10%, test 10% of boards, then take all crops of a board into the same part. If filenames do not reveal the board, cluster crops by image similarity before splitting.
- Freeze the test set. Tune on validation only.
- Keep one out-of-distribution test set (DeepPCB or the Mendeley set) that no training run ever sees.
- When comparing with a paper, check how it split; many describe a plain random ratio.

* Before using the provided train, val and test folders, run the near-duplicate check across them. Any close match between a test crop and a train crop is a warning; if matches are common, re-split by board.

**Metrics**

| Metric | What it tells you | Starting target (my proposal) |
| --- | --- | --- |
| mAP@50–95 | Detection and localisation quality across strict IoU | Match or beat the 60 to 66% range reported on this data, under your board-level split |
| Per-class recall at fixed confidence | Whether any defect type is being missed | At least 98% for open circuit, short and missing hole |
| False alarms per board (FPPB) | Operator workload | Set with the factory; start at 0.5 or fewer per board |
| Recall by defect size | Whether tiny defects fail | Report in three area buckets |
| Confusion matrix | Which classes are mixed up (short vs spurious copper, spur vs mouse bite) | Inspect, no number |
| Image AUROC, pixel AUROC, PRO | Anomaly branch quality ([Anomalib](https://github.com/open-edge-platform/anomalib) reports these) | Report on the OOD set |
| Latency per board (ms), throughput | Fits the line speed, including tiling and merging | Define from the line takt time |
| Drop vs random split | How much leakage was inflating scores | Report as a result |
| Robustness to re-compression and blur | Whether the model relies on Photoshop editing traces | Small accuracy drop; you set the limit |

The targets above are starting points I chose for discussion. The real ones depend on the cost of an escaped defect against the cost of a manual re-check on your line.

**Error analysis to include in the report.** Show the ten worst false negatives and ten worst false positives per class, with the model's confidence. A project that explains its failures is far more convincing than one that only shows a leaderboard row.

## 4. Architecture A: single-stage YOLO26 detector

**Approach.** Fine-tune a COCO-pretrained YOLO26 model to predict a box and class for every defect, in one forward pass. This is the recommended baseline: the dataset is already in YOLO format, so no conversion is needed.

**Why it fits this problem**

- **Small-object training fixes.** YOLO26 (released January 2026) adds STAL, a label-assignment rule that guarantees small objects get positive training samples, and Progressive Loss; the paper reports it targets exactly the case where tiny objects are left without positives ([Ultralytics YOLO26 paper](https://arxiv.org/abs/2606.03748), [docs](https://docs.ultralytics.com/models/yolo26/)).
- **Simple deployment.** It can run without non-maximum suppression (`nms=False`), and DFL was removed to lighten the head. The docs report up to 43% faster CPU ONNX inference for the nano model versus YOLO11n ([docs](https://docs.ultralytics.com/models/yolo26/)).
- **Five sizes.** COCO mAP@50–95 runs from 40.9 (nano, 1.7 ms on a T4 with TensorRT) to 57.5 (x, 11.8 ms), so you can trade accuracy for speed without changing code.
- **Strong PCB evidence.** On DeepPCB, YOLO26 n to x score 97.7 to 98.6% mAP@50 and 79.5 to 82.7% mAP@50–95 as plain baselines ([RefDiffNet paper](https://arxiv.org/abs/2606.00852)). Published PCB-specific YOLO variants add attention, small-target heads and better box losses on top, typically for a few points of mAP ([SME-YOLO](https://arxiv.org/abs/2601.11402v1), [PD-YOLOv8](https://doaj.org/article/779eff324b9e484d987af3be89dafaf5)).

**Recommended setup**

```python
from ultralytics import YOLO

model = YOLO("yolo26s.pt")                 # start with s; try m if recall is short
model.train(data="pcb.yaml", imgsz=640, epochs=200, batch=16)
model.val(data="pcb.yaml", split="test")
model.export(format="onnx", nms=False)     # NMS-free head for simple deployment
```

- Train at 640 first. Raise `imgsz` to 800 or 1024 only if per-class recall on thin defects (open circuit, spur) lags.
- For a stronger small-object variant, the repo ships `yolo26-p2.yaml`, which adds a P2 head. No pretrained P2 weights are released, so you would build from the YAML and transfer the matching weights from `yolo26s.pt`. Check that this works on your installed version.
- Compare against YOLO11 and YOLOv12 in the same pipeline so you can show that the newer model actually helps on your data.

**Weaknesses**

- It returns boxes only, so there is no defect shape or width measurement.
- It needs labelled defects for every class it should catch. It will not flag a defect type it never saw.
- **Licence:** the Ultralytics code and weights are AGPL-3.0 or a paid Enterprise licence ([docs](https://docs.ultralytics.com/models/yolo26/)). That is fine for a study project, but a commercial factory deployment needs a licence decision.

**Verdict:** start here. It is the fastest route to a working, measurable result and the reference every other architecture must beat.

## 5. Architecture B: real-time transformer detectors (RF-DETR, DEIMv2, RT-DETRv4)

**Approach.** Replace the YOLO head with a DETR-style detector: a transformer decoder predicts a fixed set of boxes directly, so there is no anchor tuning and no NMS step. The current real-time family has three strong options:

| Model | What is new | Reported speed and accuracy | Licence / code |
| --- | --- | --- | --- |
| [RF-DETR](https://rfdetr.roboflow.com/latest/) (ICLR 2026) | DINOv2 vision-transformer backbone; detection and instance segmentation in one API | RF-DETR-L: 56.5 AP on COCO at 6.8 ms (T4, TensorRT FP16); nano: 2.3 ms | Core package Apache 2.0; XL and 2XL models under a separate Roboflow licence ([GitHub](https://github.com/roboflow/rf-detr)) |
| [DEIMv2](https://arxiv.org/abs/2509.20787) (Sept 2025) | DINOv3 features via a Spatial Tuning Adapter; eight sizes from ultra-light to X | Code and weights on [GitHub](https://github.com/Intellindust-AI-Lab/DEIMv2) | Open code release |
| [RT-DETRv4](https://arxiv.org/abs/2510.25257) (Oct 2025) | Distils vision-foundation-model features into the detector at training time only | 49.7 / 53.5 / 55.4 / 57.0 AP (S/M/L/X) at 273 / 169 / 124 / 78 FPS | Research code |

**Why it fits this problem**

- **Better transfer from small, narrow datasets.** RF-DETR's DINOv2 backbone is described as adapting well to small datasets and domain shift, measured on the RF100-VL benchmark ([Roboflow](https://blog.roboflow.com/rf-detr/)). Your data is a narrow domain, so this matters more than COCO rank.
- **No inference cost for the extra accuracy.** RT-DETRv4 and DEIM-style training improve accuracy while leaving the deployed network unchanged ([RT-DETRv4](https://arxiv.org/abs/2510.25257), [DEIM overview](https://playground.roboflow.com/models/compare/d-fine-vs-deim)).
- **Permissive licensing.** The RF-DETR core package is Apache 2.0, which avoids the AGPL question that comes with Architecture A.
- **PCB evidence exists, but is thinner.** A plain RT-DETR scores about 81.8% mAP@50–95 on DeepPCB, similar to YOLO, and 52.8% on the harder HRIPCB ([RefDiffNet](https://arxiv.org/abs/2606.00852)). Dedicated PCB transformer papers such as MSA-DETR and Lite-DETR also exist.

**Weaknesses (my reasoning, not measured here)**

- ViT backbones work on coarse patches (14 or 16 pixels). Thin defects like a spur may be a few pixels wide, so recall on them is the thing to test first.
- DETR-style training is usually slower to converge and more sensitive to schedule than YOLO on small datasets, though DEIM-style matching was built to fix that.
- Fewer deployment tools than YOLO. Export to ONNX and TensorRT is supported for RF-DETR, but check each model's current status before committing.

**Verdict:** run it as the second experiment on the same split as Architecture A. If it wins on mAP@50–95 or on recall for thin defects, it becomes the main model. If the two tie, choose by licence and deployment target.

## 6. Architecture C: tiled inference on full boards (SAHI) with a two-stage option

**Approach.** Cut each full-resolution board image into overlapping tiles, run a detector on every tile, then merge the boxes. This is the architecture you need when the project moves from the 600 × 600 crops in the dataset to whole-board camera images. The detector inside can be a single-stage model (A or B) or a two-stage model such as Faster R-CNN.

**Why tiling is not optional on real boards**

- A 2777 × 2138 board shrunk to 640 pixels loses about 4.3× resolution, so a 63-pixel defect becomes about 15 pixels. That is my arithmetic from the board size and defect areas quoted in Section 2.
- SAHI (Slicing Aided Hyper Inference) wraps any detector with sliced inference and slicing-aided fine-tuning. On aerial benchmarks it raised AP by 5 to 7 points at inference alone and 12.7 to 14.5 points with fine-tuning ([SAHI paper](https://arxiv.org/abs/2202.06934)). Those are aerial results, so expect a smaller, different gain on PCBs.
- A 2026 follow-up, ASAHI, chooses the number of slices from image resolution and cuts inference time by 20 to 25% against SAHI ([ASAHI](https://tldr.takara.ai/p/2604.19233)).

**Cost to budget for.** With 600-pixel tiles and 20% overlap, a 2777 × 2138 board needs about 30 tiles. At the 2.5 ms T4 TensorRT figure the YOLO26s docs report for 640 inputs, that is roughly 75 ms of pure GPU time per board, before image loading and merging ([YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)). This is my estimate, not a benchmark.

**Two-stage detectors (Faster R-CNN, Cascade R-CNN)**

- A region-proposal stage followed by a box-refinement stage, available in TorchVision. They were the standard for tiny-defect work before YOLO improved and still appear in PCB papers such as TDD-Net.
- In the 2026 RefDiffNet comparison, Faster R-CNN with a ResNet-50 FPN scored 76.5% mAP@50–95 on DeepPCB and 45.0% on HRIPCB, below the YOLO and RT-DETR baselines on both ([RefDiffNet](https://arxiv.org/abs/2606.00852)).
- They are slower and heavier, so use one only as a high-recall reference model in your comparison.

**Weaknesses**

- Defects cut by a tile border are found twice or missed. Use overlap of at least the largest defect size and merge with NMS or weighted box fusion.
- Every extra tile multiplies latency. Fixed slice sizes waste work on empty copper regions.
- Train on tiles of the same size you infer on, or the benefit shrinks.

**Verdict:** treat tiling as a layer you add to A or B for production images, not as a separate model. Skip two-stage detectors as the main choice.

## 7. Architecture D: instance segmentation with SAM-generated masks

**Approach.** Predict a pixel mask for every defect instead of a box. The dataset only has boxes, so the masks must be made first: prompt Meta's Segment Anything Model 3 with each ground-truth box, keep the masks a person approves, and train a segmentation model on them. YOLO26-seg and RF-DETR-Seg are the two current candidates ([YOLO26 docs](https://docs.ultralytics.com/models/yolo26/), [RF-DETR](https://rfdetr.roboflow.com/latest/)).

**Why it fits this problem**

- **The defects are geometric.** An open circuit is a gap in a trace, a short is an unwanted bridge, a spur is a protrusion. A mask lets you measure the gap width or the extra copper area, which a box cannot.
- **Severity rules become possible.** With masks you can apply design-rule logic such as a minimum remaining trace width, which is what a real AOI line decides on.
- **Tooling is ready.** SAM 3 was released on 19 November 2025 and accepts boxes, points and masks as prompts, plus text and image examples for finding every instance of a concept ([overview](https://voxel51.com/glossary/sam-3-segment-anything-model-3)). YOLO26's segmentation head reports gains of up to 3.7 mask AP over YOLO11 on COCO ([docs](https://docs.ultralytics.com/models/yolo26/)).

**What I would not rely on.** SAM 3's text prompts are built around everyday concepts. I did not find evidence that a phrase like "short circuit on a PCB" works zero-shot, so use box prompts only. Defects a few pixels wide and low in contrast are exactly where automatic masks are least reliable (my judgment, untested here).

**Pipeline**

1. Convert each YOLO box to a box prompt and generate one mask per box with SAM 3.
2. Review a random 5% of masks per class by eye. If a class fails often, hand-correct or drop it from segmentation.
3. Train YOLO26-seg (or RF-DETR-Seg) on boxes plus approved masks.
4. Report mask IoU alongside box mAP, and measure width and area from masks.

**Weaknesses**

- Pseudo-labels carry SAM's errors into the trained model. The mask metrics only mean something if a sample was checked against human masks.
- Extra labelling effort for a benefit that matters only if you need measurements or repair guidance. For pure pass or fail, boxes are enough.
- Training and inference cost more than box-only models.

**Verdict:** an optional second phase after A or B is solid. Do it if the project goal includes defect measurement; skip it if the goal is detection and classification only.

## 8. Architecture E: unsupervised anomaly detection (Anomalib)

**Approach.** Teach a model only what a good board looks like, then flag anything that deviates, with a heatmap showing where. No defect labels are needed. The standard library is [Anomalib](https://github.com/open-edge-platform/anomalib), an Apache 2.0 project under Intel's Open Edge Platform with 23 algorithms; the most recent release I could confirm in a March 2026 guide was v2.2.0 (October 2025), so check for newer ([Datature guide](https://datature.io/blog/visual-anomaly-detection-with-anomalib-a-hands-on-guide-2026)).

| Model | Idea | Best for |
| --- | --- | --- |
| [PatchCore](https://www.amazon.science/publications/towards-total-recall-in-industrial-anomaly-detection) | Memory bank of normal patch features; score by nearest-neighbour distance | Best localisation; up to 99.6% image AUROC on MVTec AD |
| PaDiM | Gaussian model of patch features | Fast prototyping; the guide trained it in 9.2 s against 282.8 s for PatchCore |
| EfficientAd | Student–teacher distillation | Real-time edge scoring |
| [Dinomaly](https://openaccess.thecvf.com/content/CVPR2025/html/Guo_Dinomaly_The_Less_Is_More_Philosophy_in_Multi-Class_Unsupervised_Anomaly_CVPR_2025_paper.html) (CVPR 2025) | Transformer reconstruction on DINOv2 features | 99.6% / 98.7% / 89.3% image AUROC on MVTec AD / VisA / Real-IAD; in Anomalib since v2.1.0 |

Timing figures are from the [Datature guide](https://datature.io/blog/visual-anomaly-detection-with-anomalib-a-hands-on-guide-2026) on one MVTec category, so treat them as relative, not absolute. Dinomaly figures are from its [paper](https://openaccess.thecvf.com/content/CVPR2025/html/Guo_Dinomaly_The_Less_Is_More_Philosophy_in_Multi-Class_Unsupervised_Anomaly_CVPR_2025_paper.html) and [Anomalib note](https://gitee.com/github_syn/Dinomaly).

**Why it fits this problem**

- **It matches how factories actually work.** Good boards are abundant and defects are rare. It can also catch defect types nobody labelled.
- **It is evidence for a production system.** Studies on bare and assembled PCBs apply PatchCore, PaDiM, student–teacher networks and others ([PCB benchmark](https://sol.sbc.org.br/index.php/semish/article/view/43544), [student–teacher PCB paper](https://0-doi-org.brum.beds.ac.uk/10.3390/electronics10243177)).
- **Edge-ready variants are appearing.** PatchCore-Lite cuts memory by 79% for edge devices ([arXiv, March 2026](https://arxiv.org/abs/2603.20288)).

**The catch for this dataset.** Anomaly models train on defect-free images, and every image in the PKU-style data is built to contain defects. Three ways to get normal data:

1. Cut tiles that do not overlap any labelled box. Risk: unlabelled defects hiding in those tiles.
2. Use the defect-free template boards from the original PKU release (check the GitHub source the dataset card names) or from DeepPCB.
3. Collect or photograph good boards, which is the realistic production route.

**Weaknesses**

- **No defect type.** It says something is wrong, not whether it is a short or a spur. Supervised detectors usually win when labels exist ([Datature guide](https://datature.io/blog/visual-anomaly-detection-with-anomalib-a-hands-on-guide-2026)).
- **Resolution trap.** Anomalib resizes to 256 × 256 by default, which erases few-pixel defects. Raise `image_size`, or tile.
- **False positives.** Researchers working on high-resolution boards report that general-purpose anomaly detectors struggle with reflections and positional variance ([Liu et al.](https://arxiv.org/abs/2512.17296)). That paper concerns assembled boards, so bare-board behaviour may be easier.

**Verdict:** build it as a complement, not the main model. Use it to catch defects the detector misses and to flag drift in production. Evaluate with image AUROC, pixel metrics, and recall on each of your six defect types.

## 9. Architecture F: hybrid pipeline (reference image, detector and anomaly model)

**Approach.** Combine the strengths of A, B, C and E in one inspection flow. Each model covers a weakness of the others: the detector names known defects precisely, and the anomaly model catches what the detector was never trained on.

&#91;embedded content: hybrid pipeline · 2 parallel branches, 1 fusion step\]

A board is aligned and tiled, both models score every tile, and the fusion step sends known defects to the report and anything only the anomaly model flags to a person. Confirmed unknowns then become new labels for the next training round.

**What each part adds**

- **Reference-guided input enhancement.** RefDiffNet (June 2026 preprint) compares the board with an aligned defect-free reference and paints the differences into the image before the detector sees it. It added only 0.004 to 0.005 M parameters and improved mAP@50–95 across YOLOv8 to YOLO26, RT-DETR and Faster R-CNN, by up to 18% relative on HRIPCB ([paper](https://arxiv.org/abs/2606.00852)). It is a very recent preprint, so reproduce it before relying on it. It needs a registered reference image for every board design.
- **Reference-based false-alarm filtering.** Systems such as Auto-VRS and the cost-sensitive Siamese CSS-Net re-check each alarm against the reference to separate real defects from pseudo-defects ([RefDiffNet related work](https://arxiv.org/abs/2606.00852)). That matters because false alarms are what operators actually notice.
- **Anomaly branch.** Gives coverage of unseen defect types (Architecture E).
- **Tiling.** Keeps tiny defects visible on full boards (Architecture C).

**Weaknesses**

- Two models, a registration step and a fusion rule to build, calibrate and maintain.
- The reference image is only available when each board design has a golden sample. The Kaggle copy of this dataset may not include templates, so test this part on [DeepPCB](https://arxiv.org/abs/1902.06197) (1,500 aligned template and test pairs at 640 × 640).
- Alarm thresholds for the anomaly branch must be tuned against a review budget, or operators drown in unknowns.

**Verdict:** the target architecture for a production-grade system. For this project, build A first, add the tiling layer, then add the anomaly branch and fusion as the advanced phase.

## 10. Comparison and recommendation

Build A first, then B on the same split, then add tiling and the anomaly branch. Effort and role ratings below are my judgment from the evidence in Sections 4 to 9, not benchmark results.

| Architecture | Needs | Output | Best at | Main risk | Effort | Role |
| --- | --- | --- | --- | --- | --- | --- |
| A. YOLO26 detector | Box labels (have them) | Box + class | Fast, strong baseline; simple export | AGPL licence; boxes only | Low | **Main model, phase 1** |
| B. RF-DETR / DEIMv2 / RT-DETRv4 | Box labels | Box + class | Domain transfer; permissive licence (RF-DETR core) | Thin defects at coarse patch size | Medium | **Challenger, phase 2** |
| C. Tiled inference (SAHI) + optional two-stage | Full-board images | Boxes merged across tiles | Keeps tiny defects visible on real boards | Latency; tile-border duplicates | Medium | Layer on A or B for production |
| D. Instance segmentation with SAM masks | Box labels + approved masks | Pixel masks | Defect width and area measurement | Noisy pseudo-masks | Medium to high | Optional extension |
| E. Anomaly detection (Anomalib) | Defect-free images | Heatmap, no type | Unseen defect types; no defect labels | No class; false positives; resolution | Medium | Complement |
| F. Hybrid with reference image | Reference images + both models | Typed defects + unknown queue | Fewest silent misses; fewer false alarms | Two models to maintain; needs templates | High | Production target |

**Recommended plan for this project**

1. **Phase 1:** YOLO26s and YOLO26m, with YOLO11 as a control, on a board-level split. This produces your first honest numbers.
2. **Phase 2:** RF-DETR on the identical split. Keep it only if it wins on mAP@50–95 or on recall for open circuit and spur.
3. **Phase 3:** add tiled inference and test on full-board images and on an out-of-distribution set (DeepPCB or the Mendeley set from Section 2).
4. **Phase 4:** add the anomaly branch and the fusion rule, and, if you have templates, the reference-difference step.
5. **Optional:** SAM-based masks if you need measurements.

If you only have time for one architecture, choose A with a clean split and a strong write-up of failure cases. A well-evaluated baseline is worth more than a poorly evaluated hybrid.

## 11. End-to-end pipeline: data, training and tuning

The same pipeline serves Architectures A, B and C; only the model changes. Work through these steps in order.

1. **Audit the data.** Check class counts, box sizes per class, duplicate or near-duplicate crops, and a few hundred boxes by eye. Use a dataset viewer such as FiftyOne so you can filter by class and size. Fix or drop bad labels now, because every later number depends on them.
2. **Split by board.** Follow Section 3. Write the split to a file and never regenerate it.
3. **Keep native resolution.** Do not downscale the 600 × 600 crops. Train at 640 and compare 800 or 1024 only if thin-defect recall is low.
4. **Augment carefully.** The PKU boards come in two orientations ([PKU paper](https://arxiv.org/abs/1901.08204)), so flips and 90° rotations are safe. Add brightness, contrast and mild noise to mimic camera variation. Avoid heavy downscaling and aggressive crops that cut defects in half. For custom transforms use Albumentations, or the built-in Ultralytics augmentations. Mosaic can help or hurt tiny objects, so test it on and off.
5. **Fine-tune from pretrained weights.** Start from COCO weights. A reference recipe from the 2026 RefDiffNet study: 200 epochs at 640 pixels, batch 8, AdamW at 0.001 with cosine decay, 3 warm-up epochs, fixed seed ([RefDiffNet](https://arxiv.org/abs/2606.00852)). Adopt it as a starting point, not a rule.
6. **Run three seeds** of each final configuration and report mean and spread, so a 0.5-point difference is not mistaken for a win.
7. **Try the small-defect upgrades as separate ablations,** one at a time:
   - a P2 detection head for YOLO26 (`yolo26-p2.yaml`)
   - Normalized Wasserstein Distance box loss, used in [SME-YOLO](https://arxiv.org/abs/2601.11402v1) for tiny defects
   - MPDIoU loss and deformable convolution, used in DRM-YOLOv8n ([paper](https://m.researching.cn/articles/OJ582a9cfa29f8a2ba))
   - channel attention (ECA) and a BiFPN neck, used in PD-YOLOv8 ([paper](https://doaj.org/article/779eff324b9e484d987af3be89dafaf5))
   - tiled training and inference (Section 6)
8. **Tune hyperparameters last,** with the built-in Ultralytics tuner or Optuna, on the validation set only.
9. **Log everything.** Pick one tracker (Weights & Biases, MLflow or TensorBoard) and log the config, split file hash, seed and metrics for every run.
10. **Analyse failures,** then export and re-measure on the exported model, because quantised or exported models can differ from the PyTorch checkpoint.

Compute: about 10,000 images at 640 pixels is a small job. A single recent GPU, or a free Kaggle or Colab GPU, should be enough for the YOLO and RF-DETR runs (my estimate; check your own epoch times).

## 12. Tooling stack

Use Python 3.10 to 3.12 with a recent PyTorch. The Anomalib command line had import problems on Python 3.14 in a March 2026 test, so the older versions are the safe choice ([Datature guide](https://datature.io/blog/visual-anomaly-detection-with-anomalib-a-hands-on-guide-2026)). The last column says what I could confirm from sources opened for this report; "not checked" means a widely used tool whose current version I did not verify.

| Layer | Tool | Role in this project | Confirmed status |
| --- | --- | --- | --- |
| Detector, CNN | [Ultralytics YOLO26](https://docs.ultralytics.com/models/yolo26/) | Architecture A, export, segmentation variant | Released 14 Jan 2026; paper June 2026; AGPL-3.0 or Enterprise licence; docs list a YOLO27 as "coming soon" |
| Detector, transformer | [RF-DETR](https://github.com/roboflow/rf-detr) | Architecture B, also segmentation | ICLR 2026; core Apache 2.0 |
| Detector, transformer | [DEIMv2](https://github.com/Intellindust-AI-Lab/DEIMv2), [RT-DETRv4](https://arxiv.org/abs/2510.25257) | Architecture B alternatives | Sept 2025 and Oct 2025 papers |
| Small objects | [SAHI](https://arxiv.org/abs/2202.06934) | Tiled inference and fine-tuning | ICIP 2022; adaptive variant ASAHI, April 2026 |
| Anomaly detection | [Anomalib](https://github.com/open-edge-platform/anomalib) | PatchCore, PaDiM, EfficientAd, Dinomaly | v2.2.0 (Oct 2025) in the March 2026 guide; Apache 2.0 |
| Segmentation | [SAM 3](https://github.com/facebookresearch/sam3) | Box-prompted pseudo-masks | Released 19 Nov 2025 |
| Registration | OpenCV (ECC alignment) | Aligns board to reference | Not checked; RefDiffNet names ECC as its alignment step |
| Data inspection | FiftyOne, CVAT or Label Studio | Audit, relabel, error browsing | Not checked |
| Augmentation | Albumentations | Custom transforms | Not checked |
| Tracking | Weights & Biases, MLflow or TensorBoard | Experiment log | Not checked |
| Export and runtime | ONNX, TensorRT, OpenVINO, ONNX Runtime | Deployment (Section 13) | YOLO26 exports to these; Ultralytics docs note TensorRT 11.0 lacks DLA support, so use 10.x for Jetson DLA |

What I deliberately left out: older YOLO versions as the main model (YOLO26 is the current Ultralytics recommendation for new projects, per its [docs comparison pages](https://docs.ultralytics.com/compare/yolo11-vs-yolo26)), and vision-language models. A VLM could write plain-language defect explanations for operators, but I found no PCB-specific evidence worth building a section on.

## 13. Deployment and optimisation

Deploy through an exported model, not the training checkpoint, and re-measure accuracy after every conversion. YOLO26 exports to TensorRT, ONNX, CoreML, LiteRT and OpenVINO ([docs](https://docs.ultralytics.com/models/yolo26/)).

| Target | Runtime | Notes |
| --- | --- | --- |
| NVIDIA GPU server | TensorRT, FP16 or INT8 | INT8 uses post-training quantisation and needs calibration images from your own boards ([TensorRT export docs](https://docs.ultralytics.com/integrations/tensorrt?h=yolov8)) |
| NVIDIA Jetson | TensorRT engine built on the device | Usual path is PyTorch to ONNX to TensorRT engine; set the power mode before benchmarking ([Seeed tutorial](https://sensecraft.seeed.cc/ai-lab/tutorials/j/computer-vision/model-export-and-edge-deployment)) |
| Intel CPU or integrated GPU | OpenVINO | Anomalib exports PatchCore and others to OpenVINO with `anomalib export --export_type openvino` ([Datature guide](https://datature.io/blog/visual-anomaly-detection-with-anomalib-a-hands-on-guide-2026)) |
| Any CPU | ONNX Runtime | Slowest option; see the CPU budget below |

**Compression has a measured cost.** On a PCB study, pruning and quantising YOLOv9-small cut model size by 36.4% and raised speed by 24.7%, while mAP@50 moved from 99.2% to 98.6% ([study](https://www.sciopen.com/article/10.32604/cmc.2026.080112)). That is a good trade only if recall on fatal defects stays within your target, so check per-class recall, not just mAP.

**Latency budget.** Using the Ultralytics figures for YOLO26 at 640 pixels: the small model takes 2.5 ms on a T4 with TensorRT, and the nano model 38.9 ms on a 2 GHz Xeon with ONNX ([docs](https://docs.ultralytics.com/models/yolo26/)). With about 30 tiles per board (Section 6), that is roughly 75 ms of GPU time versus over a second per board on that CPU for the nano model. These are my estimates from vendor numbers. Measure on your own hardware and image sizes.

**Serving shape.** Camera capture, then a queue, then an inference service that tiles, runs the models and fuses results, then a verdict sent to the line controller or a review screen. Keep the anomaly model's memory bank small; PatchCore-Lite reports a 79% memory cut for edge devices ([arXiv](https://arxiv.org/abs/2603.20288)).

**After go-live**

- Log every verdict with the image, so reviewers' corrections become new training data.
- Watch the distribution of anomaly scores and detector confidences. A shift usually means a lighting, camera or supplier change.
- Re-evaluate on a fresh sample of boards on a schedule, and retrain only against the frozen test set protocol from Section 3.
- Decide the licence route for Ultralytics models (AGPL-3.0 or Enterprise) before any commercial use.

## 14. Roadmap, risks and deliverables

Plan for five phases with a gate after each of the first four, so a weak result stops early instead of carrying forward. I assume part-time work over roughly 8 to 10 weeks; adjust to your deadline, since you did not give one.

&#91;embedded content: project roadmap · 5 phases, 4 gates\]

Phase 1 is a complete project on its own. Everything after it adds depth.

**Risks and how to handle them**

| Risk | Why it matters | Mitigation |
| --- | --- | --- |
| Leakage between train and test crops | Inflates every score | Board-level split; report the drop against a random split |
| Synthetic-to-real gap | A model that is near-perfect here may fail on real boards | Out-of-distribution test sets; photograph a few real boards if you can |
| Low recall on thin defects | Open circuits and spurs are the costly misses | Tiling, higher input size, P2 head, per-class recall as the gate |
| No defect-free images for the anomaly branch | Architecture E cannot train | Box-free tiles, template boards, or new good-board photos (Section 8) |
| Dataset details unverified | Image size and licence terms are unconfirmed; the card lists the licence only as Other | Check the dataset files and licence before Phase 1 |
| Preprint results do not reproduce | RefDiffNet is a June 2026 preprint | Treat it as an experiment, with a fallback to the plain detector |
| Licence for commercial use | AGPL-3.0 for Ultralytics models | Decide between the Enterprise licence and RF-DETR's Apache 2.0 core |
| Photoshop-drawn defects leave traces | The model may learn editing artifacts, not real defects | Re-compression and blur tests; evaluate on real boards (Mendeley set) |
| Provided splits probably leak | Crops of one board in train and test inflate scores | Run the leakage check; re-split by board if matches are common |

**Deliverables**

- Cleaned dataset notes, the board-level split file and training configs.
- Trained and exported models with the full metric tables from Section 3.
- An ablation table showing which small-defect upgrades helped.
- A failure-analysis gallery per class.
- A simple demo that takes a board image, tiles it, and draws the results.
- A short final report that states what was and was not tested.

## Sources

Research done on 10 October 2026. Model and library versions move quickly, so recheck release pages before you pin versions.

**Opened in full**

- [Kaggle: PCB Defects Dataset](https://www.kaggle.com/datasets/fedybenhassouna/printed-circuit-board-pcb-defects) (only the page title and description were readable)
- [Ultralytics YOLO26 documentation](https://docs.ultralytics.com/models/yolo26/)
- [RefDiffNet: Learning to Expose Subtle PCB Defects Before Detection](https://arxiv.org/abs/2606.00852)
- [Datature: Visual Anomaly Detection with Anomalib (March 2026)](https://datature.io/blog/visual-anomaly-detection-with-anomalib-a-hands-on-guide-2026)

**Read as search excerpts, not opened in full**

- Datasets: [PKU PCB dataset paper](https://arxiv.org/abs/1901.08204), [DeepPCB](https://arxiv.org/abs/1902.06197), [Augmented PCB Defect on DatasetNinja](https://datasetninja.com/augmented-pcb-defect), [ESRPCB](https://arxiv.org/pdf/2506.13476), [Mendeley PCB-Defect set](https://data.mendeley.com/datasets/vdj74sngvn/1)
- Detectors: [YOLO26 paper](https://arxiv.org/abs/2606.03748), [RF-DETR docs](https://rfdetr.roboflow.com/latest/), [RT-DETRv4](https://arxiv.org/abs/2510.25257), [DEIMv2](https://arxiv.org/abs/2509.20787), [D-FINE vs DEIM summary](https://playground.roboflow.com/models/compare/d-fine-vs-deim), [YOLO11 vs YOLO26](https://docs.ultralytics.com/compare/yolo11-vs-yolo26)
- PCB detector papers: [SME-YOLO](https://arxiv.org/abs/2601.11402v1), [PD-YOLOv8](https://doaj.org/article/779eff324b9e484d987af3be89dafaf5), [DRM-YOLOv8n](https://m.researching.cn/articles/OJ582a9cfa29f8a2ba), [optimised YOLOv9 PCB study](https://www.sciopen.com/article/10.32604/cmc.2026.080112)
- Tiling and segmentation: [SAHI](https://arxiv.org/abs/2202.06934), [ASAHI](https://tldr.takara.ai/p/2604.19233), [SAM 3 overview](https://voxel51.com/glossary/sam-3-segment-anything-model-3)
- Anomaly detection: [PatchCore](https://www.amazon.science/publications/towards-total-recall-in-industrial-anomaly-detection), [Dinomaly (CVPR 2025)](https://openaccess.thecvf.com/content/CVPR2025/html/Guo_Dinomaly_The_Less_Is_More_Philosophy_in_Multi-Class_Unsupervised_Anomaly_CVPR_2025_paper.html), [PatchCore-Lite](https://arxiv.org/abs/2603.20288), [PCB anomaly benchmark](https://sol.sbc.org.br/index.php/semish/article/view/43544), [student–teacher PCB paper](https://0-doi-org.brum.beds.ac.uk/10.3390/electronics10243177), [pixel-wise PCBA anomaly location](https://arxiv.org/abs/2512.17296)
- Deployment: [Ultralytics TensorRT export](https://docs.ultralytics.com/integrations/tensorrt?h=yolov8), [Seeed Jetson export tutorial](https://sensecraft.seeed.cc/ai-lab/tutorials/j/computer-vision/model-export-and-edge-deployment)
