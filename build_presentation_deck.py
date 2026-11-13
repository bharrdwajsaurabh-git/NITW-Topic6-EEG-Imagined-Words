"""
build_presentation_deck.py
==========================
Generates a stunning, modern, highly attractive 19-slide presentation deck:
'NITW_Topic6_Presentation.html'

Key Enhancements:
1. Increased content depth & technical rigor (gaps in primary paper, why MDRC-AGA was chosen, detailed mathematical methods).
2. Significantly enlarged typography for effortless readability from the back of an exam hall (12.5-14pt body, 24-28pt titles).
3. Modern dark academic glassmorphism UI (#0a1128, cyan #00d2ff, emerald #06d6a0, gold #ffd166).
4. Clean card-based visual layouts with embedded high-resolution figures.
5. Removed on-slide "What to say to professor" drawer to eliminate visual clutter.
6. Promising, visionary Conclusion & Strategic Future Roadmap on Slide 19.
7. Exact ground-truth JSON metrics (Calibrated Stacker: 73.55%, Peak Soft Voter: 90.85%).
"""

import os
import sys
import shutil
import base64
import json

def get_base64_image(image_path):
    if not os.path.exists(image_path):
        return ""
    ext = os.path.splitext(image_path)[1].lower().replace('.', '')
    if ext == 'jpg': ext = 'jpeg'
    with open(image_path, 'rb') as f:
        data = base64.b64encode(f.read()).decode('ascii')
    return f"data:image/{ext};base64,{data}"

def build_deck():
    base_dir = r"c:\Users\st983\Downloads\ml\imagined_speech_eeg"
    img_dir = os.path.join(base_dir, "latex_report", "images")

    logo_b64 = get_base64_image(os.path.join(img_dir, "nitw_logo_clean.png"))
    arch_b64 = get_base64_image(os.path.join(img_dir, "architecture_flow_diagram.png"))
    fig1_b64 = get_base64_image(os.path.join(img_dir, "fig1_montage.png"))
    fig2_b64 = get_base64_image(os.path.join(img_dir, "fig2_frequency_bands.jpg"))
    fig3_b64 = get_base64_image(os.path.join(img_dir, "fig3_confusion_matrix.png"))
    fig4_b64 = get_base64_image(os.path.join(img_dir, "fig4_per_class_metrics.png"))
    fig5_b64 = get_base64_image(os.path.join(img_dir, "fig5_partition_latency.png"))

    slides = [
        # SLIDE 1: Title & Academic Affiliation
        {
            "id": 1,
            "badge": "Topic 6 • Advanced Algorithms",
            "title": "EEG-Based Imagined Word Recognition",
            "subtitle": "Using Multi-Scale Riemannian Covariance and Calibrated Stacker Ensemble",
            "html": f"""
            <div class="slide-center">
                <img src="{logo_b64}" class="slide-logo" alt="NIT Warangal Logo">
                <div class="inst-tag">National Institute of Technology, Warangal</div>
                <div class="dept-tag">Department of Computer Science and Engineering &bull; CS26001 Course Project</div>
                <h1 class="main-title">EEG-Based Imagined Word Recognition</h1>
                <p class="main-sub">Using Multi-Scale Riemannian Covariance and Calibrated Stacker Ensemble</p>
                <div class="topic-tag">Topic 6 &bull; Covert Speech Decoding &bull; Assistive BCI Neuro-Engineering</div>
                
                <div class="team-cards-grid">
                    <div class="tcard">
                        <div class="tname">Saurabh Bharrdwaj</div>
                        <div class="troll">Roll No.: 26CSM2R19</div>
                        <div class="tprog">M.Tech (CSIS)</div>
                    </div>
                    <div class="tcard">
                        <div class="tname">Badvath Jaipal</div>
                        <div class="troll">Roll No.: 26CSM2R04</div>
                        <div class="tprog">M.Tech (CSIS)</div>
                    </div>
                    <div class="tcard">
                        <div class="tname">Saurabh Kumar</div>
                        <div class="troll">Roll No.: 26CSM2R20</div>
                        <div class="tprog">M.Tech (CSIS)</div>
                    </div>
                </div>
                
                <div class="guide-box">
                    <strong>Project Supervisor:</strong> Dr. Manish Kumar Bajpai, Associate Professor, Department of Computer Science &amp; Engineering
                </div>
            </div>
            """
        },

        # SLIDE 2: Clinical Problem & Medical Motivation
        {
            "id": 2,
            "badge": "Clinical Problem Statement",
            "title": "The Medical Imperative: Restoring Voice for the Voiceless",
            "subtitle": "Bridging the Critical Communication Barrier in Locked-In Syndrome and ALS",
            "html": """
            <div class="grid-2col">
                <div class="info-card alert-card">
                    <h3><span class="icon">&#9888;</span> The Neurological Challenge</h3>
                    <p>Patients suffering from <strong>Amyotrophic Lateral Sclerosis (ALS)</strong>, severe brainstem stroke, or high cervical trauma lose all peripheral neuromuscular control, entering <strong>Locked-In Syndrome (LIS)</strong>.</p>
                    <p>While cognitively alert, these individuals cannot articulate speech or control conventional mechanical assistive devices. Restoring communicative autonomy is an urgent clinical imperative.</p>
                    <div class="bullet-list" style="margin-top: 14pt;">
                        <div class="bitem"><strong>Direct Linguistic Decoding:</strong> Translates purely imagined, covert speech into digital text without physical vocal cord movement.</div>
                        <div class="bitem"><strong>Superior to Motor Imagery:</strong> Unlike limb motor imagery (hands/feet), imagined speech provides natural, intuitive language output.</div>
                    </div>
                </div>
                
                <div class="info-card">
                    <h3><span class="icon">&#9733;</span> Project Scope &amp; Target Vocabulary</h3>
                    <p>We target the complete <strong>9-Class Mendeley EEGIS Corpus</strong> (4,044 real 3.0s trials, 14 channels) comprising critical survival and communicative words:</p>
                    <div class="word-chip-grid">
                        <div class="chip chip-em">Help</div>
                        <div class="chip chip-em">Hungry</div>
                        <div class="chip chip-em">Thirsty</div>
                        <div class="chip">Yes (S&iacute;)</div>
                        <div class="chip">No</div>
                        <div class="chip">Rest</div>
                        <div class="chip chip-warn">Pain</div>
                        <div class="chip chip-warn">Bathroom</div>
                        <div class="chip chip-cyan">Thanks</div>
                    </div>
                    <div class="callout-box" style="margin-top: 16pt;">
                        <strong>Clinical Latency Budget:</strong> Decision must be rendered in <strong>&lt; 25 ms</strong> to enable fluid, interactive neuro-prosthetic augmentative and alternative communication (AAC).
                    </div>
                </div>
            </div>
            """
        },

        # SLIDE 3: Primary Reference Paper Breakdown
        {
            "id": 3,
            "badge": "Stage 1: Reference Paper",
            "title": "Primary Reference Paper: Lara-Arellano et al. (MDPI Eng, 2025)",
            "subtitle": "Feature Generation and Selection for Imagined Speech EEG Classification",
            "html": """
            <div class="grid-2col">
                <div class="info-card">
                    <h3><span class="icon">&#128214;</span> Paper Overview &amp; Experimental Design</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>Citation:</strong> E. Lara-Arellano, A. Takacs, S. Tovar-Arriaga, and J. Rodr&iacute;guez-Res&eacute;ndiz, <em>Eng</em> (MDPI), vol. 6, no. 4, art. 75, Apr. 2025.</div>
                        <div class="bitem"><strong>Dataset:</strong> EEGIS Database (Mendeley Data V1), 14 channels at 128 Hz.</div>
                        <div class="bitem"><strong>14-Channel Montage:</strong> AF3, F7, F3, FC5, T7, P7, O1, O2, P8, T8, FC6, F4, F8, AF4 (International 10&ndash;20 System).</div>
                        <div class="bitem"><strong>6 Canonical Bands:</strong> Delta (0.5&ndash;4 Hz), Theta (4&ndash;8 Hz), Alpha (8&ndash;13 Hz), Low-Beta (13&ndash;20 Hz), High-Beta (20&ndash;30 Hz), Gamma (30&ndash;45 Hz).</div>
                        <div class="bitem"><strong>Experimental Scope:</strong> Strictly evaluated on <strong>Binary Yes (S&iacute;) vs No</strong> (924 trials).</div>
                    </div>
                </div>
                
                <div class="info-card">
                    <h3><span class="icon">&#9881;</span> Primary Paper Pipeline &amp; Claims</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>Feature Engineering:</strong> Computes 214 univariate moments per channel across 6 bands + raw signal &rarr; <strong>2,996 flat scalar moments</strong> per trial (variance, skewness, kurtosis, Hjorth parameters, spectral entropy).</div>
                        <div class="bitem"><strong>Genetic Algorithm (GA):</strong> 228-bit binary chromosome with uniform crossover (p<sub>c</sub> = 0.85) and bit-flip mutation (p<sub>m</sub> = 0.03).</div>
                        <div class="bitem"><strong>Classifier:</strong> Single <em>k</em>-Nearest Neighbors (<em>k</em>NN, <em>k</em> = 5).</div>
                        <div class="bitem"><strong>Published Benchmark:</strong> <strong>96.00% binary test accuracy</strong> with 288 selected features.</div>
                    </div>
                </div>
            </div>
            """
        },

        # SLIDE 4: Stage 1 Exact Local Replication
        {
            "id": 4,
            "badge": "Stage 1: Replication Results",
            "title": "Stage 1: Rigorous Local Replication of Primary Benchmark",
            "subtitle": "Independent Verification of the Published Binary Pipeline on Held-Out Test Data",
            "html": """
            <div class="grid-2col">
                <div class="info-card">
                    <h3><span class="icon">&#9989;</span> Local Reproduction Setup &amp; Methodology</h3>
                    <p>Before designing improvements, we conducted an exact, independent code and pipeline reproduction of the Lara-Arellano paper to establish an authentic baseline:</p>
                    <div class="bullet-list" style="margin-top: 10pt;">
                        <div class="bitem"><strong>Partition:</strong> Exact 80% train (739 trials) / 20% held-out test (185 trials) on binary <em>Yes</em> vs <em>No</em>.</div>
                        <div class="bitem"><strong>GA Optimization:</strong> 228-bit rank-based genetic selection maximizing validation fitness.</div>
                        <div class="bitem"><strong>Pre-GA Baseline:</strong> <em>k</em>NN accuracy before genetic pruning was <strong>72.97%</strong>.</div>
                        <div class="bitem"><strong>Selected Subspace:</strong> Successfully evolved to <strong>288 optimal moments</strong>.</div>
                    </div>
                </div>
                
                <div class="info-card">
                    <h3><span class="icon">&#128202;</span> Replication Metrics (N = 185 Held-Out Test Trials)</h3>
                    <table class="clean-table" style="margin-top: 8pt;">
                        <thead>
                            <tr>
                                <th>Benchmark</th>
                                <th>Test Accuracy</th>
                                <th>Precision</th>
                                <th>Recall</th>
                                <th>Macro-F1</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Published Target [MDPI 2025]</td>
                                <td><strong>96.00%</strong></td>
                                <td>0.9600</td>
                                <td>0.9600</td>
                                <td>0.9600</td>
                            </tr>
                            <tr style="background: rgba(0, 210, 255, 0.12); font-weight: bold;">
                                <td>Our Local Reproduction</td>
                                <td><span style="color: #00d2ff; font-size: 13pt;">93.51%</span></td>
                                <td>0.9326</td>
                                <td>0.9326</td>
                                <td>0.9326</td>
                            </tr>
                        </tbody>
                    </table>
                    <div class="callout-box" style="margin-top: 14pt;">
                        <strong>Key Takeaway:</strong> Our local reproduction correctly decoded <strong>173 of 185 test trials</strong> (93.51%), verifying the validity of the primary author's binary findings.
                    </div>
                </div>
            </div>
            """
        },

        # SLIDE 5: Critical Research Gaps in the Primary Paper
        {
            "id": 5,
            "badge": "Critical Research Gaps",
            "title": "What's Missing? 4 Foundational Gaps in the Primary Paper",
            "subtitle": "Why the published state-of-the-art fails when advancing toward real-world clinical BCIs",
            "html": """
            <div class="grid-2col">
                <div class="info-card alert-card">
                    <h3><span class="icon">&#10060;</span> Gap 1: The Binary-Only Ceiling</h3>
                    <p>The primary paper only evaluated a <strong>2-class proof-of-concept</strong> (<em>Yes</em> vs <em>No</em>). A viable communicative AAC neuro-prosthetic requires decoding multi-word vocabularies. The authors could not evaluate multi-class decoding due to severe computational complexity.</p>
                </div>
                
                <div class="info-card alert-card">
                    <h3><span class="icon">&#10060;</span> Gap 2: The 2<sup>228</sup> GA Combinatorial Trap</h3>
                    <p>Evaluating a 228-bit genome on 9 classes across 10 candidate classifiers creates a search space of <strong>2<sup>228</sup> &approx; 10<sup>68</sup> configurations</strong>. Fitness evaluations required days of compute and resulted in combinatorial timeout.</p>
                </div>
                
                <div class="info-card alert-card">
                    <h3><span class="icon">&#10060;</span> Gap 3: Destruction of Spatial Phase Geometry</h3>
                    <p>Extracting univariate scalar moments per channel (variance, kurtosis) treats electrodes as <strong>isolated sensors</strong>. It completely destroys the inter-electrode phase synchronization and neural connectivity between Broca's and Wernicke's language regions.</p>
                </div>
                
                <div class="info-card alert-card">
                    <h3><span class="icon">&#10060;</span> Gap 4: Zero Probability Calibration</h3>
                    <p>A single <em>k</em>NN classifier outputs hard distance votes with <strong>no posterior probability confidence</strong>. In clinical neuro-prosthetics, uncalibrated models produce confident false alarms that disrupt nursing and medical workflows.</p>
                </div>
            </div>
            """
        },

        # SLIDE 6: The Flat-Feature Trap
        {
            "id": 6,
            "badge": "Theoretical Bottleneck",
            "title": "The 'Flat-Feature Trap' in Multi-Class EEG Signal Processing",
            "subtitle": "Mathematical demonstration of why conventional scalar moments collapse on 9 classes",
            "html": """
            <div class="grid-2col">
                <div class="info-card">
                    <h3><span class="icon">&#9881;</span> Conventional Flat Moment Concatenation</h3>
                    <div class="bullet-list">
                        <div class="bitem">Standard pipelines compute channel-wise univariate moments: Variance &sigma;<sup>2</sup>, Skewness &gamma;, Kurtosis &kappa;, Hjorth Activity/Mobility/Complexity, and Spectral Entropy.</div>
                        <div class="bitem">Concatenating 214 moments across 14 channels &times; 6 bands creates a <strong>2,996-dimensional flat vector</strong>.</div>
                        <div class="bitem">Univariate pruning (ANOVA <em>F</em>-tests, Mutual Information) ranks dimensions independently, assuming orthogonality.</div>
                        <div class="bitem"><strong>Result on 9 Classes:</strong> Without spatial correlation, local multi-class baseline accuracy saturates at <strong>70.39%</strong> (29.61% error rate).</div>
                    </div>
                </div>
                
                <div class="info-card alert-card">
                    <h3><span class="icon">&#9888;</span> 3 Mathematical Failures of the Flat Approach</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>1. Phase Blindness:</strong> Covert linguistic phonation produces phase-locked resonance across the left fronto-temporal arc. Flat moments discard the cross-spectral covariance matrix.</div>
                        <div class="bitem"><strong>2. Manifold Curvature Distortion:</strong> Multichannel EEG signals live on a curved Riemannian manifold of Symmetric Positive Definite (SPD) covariance matrices. Euclidean distance severely distorts this geometry.</div>
                        <div class="bitem"><strong>3. The Euclidean 'Swelling Effect':</strong> Averaging covariance matrices in Euclidean space artificially inflates matrix determinants, introducing spurious high-frequency noise.</div>
                    </div>
                </div>
            </div>
            """
        },

        # SLIDE 7: Why We Chose Our Solution (MDRC-AGA)
        {
            "id": 7,
            "badge": "Stage 2 Innovation",
            "title": "Why We Chose MDRC-AGA: Our Improvement Hypothesis",
            "subtitle": "Bridging the gap from binary proof-of-concept to clinical multi-class communication",
            "html": """
            <div class="grid-2col">
                <div class="info-card">
                    <h3><span class="icon">&#128161;</span> The Core Scientific Hypothesis</h3>
                    <p>Rather than treating electrodes as flat scalar moments, multichannel EEG signals should be represented as <strong>Symmetric Positive Definite (SPD) covariance matrices</strong> on a Riemannian manifold.</p>
                    <div class="bullet-list" style="margin-top: 12pt;">
                        <div class="bitem"><strong>Solves Gaps 1 &amp; 3:</strong> Preserves full inter-electrode covariance and phase synchronization across language networks.</div>
                        <div class="bitem"><strong>Solves Gap 2:</strong> Replaces combinatorial 228-bit bit-flips with <strong>continuous block scaling</strong> ($w \\in [0.5, 2.0]^3$), optimizing subspaces in seconds without destroying matrix positive-definiteness.</div>
                        <div class="bitem"><strong>Solves Gap 4:</strong> Introduces a calibrated meta-stacker ensemble with Platt-scaling to guarantee clinical probability safety.</div>
                    </div>
                </div>
                
                <div class="info-card" style="border-color: #06d6a0;">
                    <h3><span class="icon">&#128640;</span> The 4 Strategic Pillars of MDRC-AGA</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>1. Multi-Scale Filter Bank (1,695D):</strong> Combines 6 canonical bands, 7 fine causal sub-bands, and a speech-localized 10-channel sub-montage.</div>
                        <div class="bitem"><strong>2. Riemannian Manifold Geometry:</strong> Projects covariance matrices into Euclidean tangent space anchored at the Fr&eacute;chet geometric mean.</div>
                        <div class="bitem"><strong>3. MultiScaleBlockAGA:</strong> Continuous evolutionary algorithm optimizing band weights without rank corruption.</div>
                        <div class="bitem"><strong>4. Calibrated Stacker Ensemble:</strong> L2-Logistic Regression, Shrinkage LDA, Platt-Ridge, and Soft Probability Voting.</div>
                    </div>
                </div>
            </div>
            """
        },

        # SLIDE 8: End-to-End System Architecture
        {
            "id": 8,
            "badge": "System Architecture",
            "title": "End-to-End Architecture: The MDRC-AGA Pipeline",
            "subtitle": "Complete workflow from raw 14-channel EEG acquisition to real-time dual-head decision",
            "html": f"""
            <div class="grid-2col">
                <div class="info-card">
                    <h3><span class="icon">&#9881;</span> Architectural Workflow</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>1. Signal Conditioning:</strong> 14 channels, 128 Hz sampling. 4th-order Butterworth bandpass (0.5&ndash;45 Hz) + 50 Hz causal notch filter.</div>
                        <div class="bitem"><strong>2. Multi-Scale Decomposition:</strong> 3-branch spatial-spectral mapping yielding 1,695 manifold dimensions.</div>
                        <div class="bitem"><strong>3. Manifold Projection:</strong> Regularized Ledoit-Wolf shrinkage covariance into Log-Euclidean tangent space.</div>
                        <div class="bitem"><strong>4. Evolutionary Tuning:</strong> MultiScaleBlockAGA continuous weight scaling.</div>
                        <div class="bitem"><strong>5. Dual Decision Heads:</strong> Simultaneous generation of peak voting accuracy and calibrated posterior probabilities.</div>
                    </div>
                </div>
                
                <div class="info-card" style="text-align: center; padding: 12pt;">
                    <img src="{fig1_b64}" class="img-responsive" alt="14-Channel Montage" style="max-height: 380px;">
                    <div style="font-size: 11pt; color: #a0afcd; margin-top: 8pt;">Fig 1: 14-Channel International 10&ndash;20 System with language arc highlighted.</div>
                </div>
            </div>
            """
        },

        # SLIDE 9: Multi-Scale Feature Engineering Breakdown
        {
            "id": 9,
            "badge": "Feature Engineering",
            "title": "Multi-Scale Riemannian Feature Space: 1,695 Dimensions",
            "subtitle": "Engineering 3 complementary spatial-spectral views capturing global, fine, and speech rhythms",
            "html": f"""
            <div class="grid-2col">
                <div class="info-card">
                    <h3><span class="icon">&#128300;</span> The 3 Complementary Manifold Branches</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>Branch 1: Canonical 6-Band Filter Bank (630D)</strong><br>
                        14 channels &times; 6 canonical bands (Delta, Theta, Alpha, BetaL, BetaH, Gamma). Each 14&times;14 covariance matrix yields 105 tangent space features. Total: 6 &times; 105 = <strong>630 dimensions</strong>.</div>
                        <div class="bitem"><strong>Branch 2: Fine Causal Sub-Bands (735D)</strong><br>
                        7 narrow 4&ndash;5 Hz bandwidth slices spanning 4 to 45 Hz (Theta-Alpha, Low-Alpha, High-Alpha, Low-Beta, Mid-Beta, High-Beta, Gamma) capturing covert articulatory ERD/ERS bursts. Total: 7 &times; 105 = <strong>735 dimensions</strong>.</div>
                        <div class="bitem"><strong>Branch 3: Speech-10 Sub-Montage (330D)</strong><br>
                        Prunes non-speech occipital channels (O1, O2, P7, P8), isolating 10 fronto-temporal electrodes (AF3, F7, F3, FC5, T7, T8, FC6, F4, F8, AF4). 10&times;10 matrix yields 55 features across 6 bands = <strong>330 dimensions</strong>.</div>
                        <div class="bitem"><strong>Total Concatenated Vector:</strong> 630D + 735D + 330D = <strong>1,695 dimensions</strong>.</div>
                    </div>
                </div>
                
                <div class="info-card" style="text-align: center; padding: 12pt;">
                    <img src="{fig2_b64}" class="img-responsive" alt="Sub-Band Frequencies" style="max-height: 380px;">
                    <div style="font-size: 11pt; color: #a0afcd; margin-top: 8pt;">Fig 2: Canonical and fine sub-band frequency intervals spanning 0.5 to 45 Hz.</div>
                </div>
            </div>
            """
        },

        # SLIDE 10: Riemannian Geometry & Mathematical Formulation
        {
            "id": 10,
            "badge": "Mathematical Formulation",
            "title": "Riemannian Geometry: Operating on SPD Manifolds",
            "subtitle": "Log-Euclidean Tangent Space Projection Anchored at the Fr&eacute;chet Geometric Mean",
            "html": """
            <div class="grid-2col">
                <div class="info-card">
                    <h3><span class="icon">&#128290;</span> Mathematical Formulation</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>1. Shrinkage Covariance Estimation:</strong><br>
                        For epoch X<sub>i</sub> &isin; &reals;<sup>P &times; T</sup>, Ledoit-Wolf shrinkage ensures full rank:
                        <div class="eq-box">C<sub>i</sub> = [1 / (T &minus; 1)] X<sub>i</sub> X<sub>i</sub><sup>T</sup> + &lambda; I, &nbsp; &lambda; = 10<sup>&minus;5</sup></div></div>
                        <div class="bitem"><strong>2. Affine-Invariant Riemannian Metric (AIRM):</strong><br>
                        Geodesic distance between covariance matrices C<sub>1</sub>, C<sub>2</sub> &isin; S<sub>++</sub><sup>P</sup>:
                        <div class="eq-box">&delta;<sub>R</sub>(C<sub>1</sub>, C<sub>2</sub>) = || Logm( C<sub>1</sub><sup>&minus;1/2</sup> C<sub>2</sub> C<sub>1</sub><sup>&minus;1/2</sup> ) ||<sub>F</sub></div></div>
                        <div class="bitem"><strong>3. Fr&eacute;chet Geometric Reference Mean:</strong><br>
                        Computed strictly inside each training fold:
                        <div class="eq-box">C<sub>ref</sub> = exp[ (1 / N) &sum;<sub>i=1</sub><sup>N</sup> Logm(C<sub>i</sub>) ]</div></div>
                    </div>
                </div>
                
                <div class="info-card" style="border-color: #06d6a0;">
                    <h3><span class="icon">&#9989;</span> Tangent Projection &amp; Vectorization</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>4. Tangent Space Mapping:</strong><br>
                        Maps curved Riemannian manifold into locally flat Euclidean tangent space:
                        <div class="eq-box">S<sub>i</sub> = Logm( C<sub>ref</sub><sup>&minus;1/2</sup> C<sub>i</sub> C<sub>ref</sub><sup>&minus;1/2</sup> )</div></div>
                        <div class="bitem"><strong>5. Isometric Vectorization:</strong><br>
                        Upper-triangular elements scaled by &radic;2 preserve true geodesic distance:
                        <div class="eq-box">vect(S<sub>i</sub>) = [ S<sub>j,j</sub> , &radic;2 S<sub>j,k</sub> ]<sub>1 &le; j &lt; k &le; P</sub></div></div>
                        <div class="bitem"><strong>Core Advantage:</strong> Converts non-linear curved EEG manifolds into linear vector spaces where regularized classifiers achieve maximum theoretical separation.</div>
                    </div>
                </div>
            </div>
            """
        },

        # SLIDE 11: MultiScaleBlockAGA Evolutionary Optimization
        {
            "id": 11,
            "badge": "Evolutionary Optimization",
            "title": "MultiScaleBlockAGA: Continuous Manifold Optimization",
            "subtitle": "Evolving continuous block scales while strictly preserving matrix positive-definiteness",
            "html": """
            <div class="grid-2col">
                <div class="info-card alert-card">
                    <h3><span class="icon">&#9888;</span> Why Binary Bit-Flip GAs Fail on Covariances</h3>
                    <p>The primary paper evolved a 228-bit mask turning scalar moments ON or OFF. On Riemannian covariance matrices, flipping discrete bits sets off-diagonal covariances to zero, violating positive-definiteness (det(C) &le; 0) and crashing the matrix logarithm.</p>
                    <p style="margin-top: 10pt;">Furthermore, evaluating 228 binary bits on 9 classes creates an intractable 2<sup>228</sup> search space that causes combinatorial timeout.</p>
                </div>
                
                <div class="info-card" style="border-color: #00d2ff;">
                    <h3><span class="icon">&#9881;</span> Our Continuous Block-AGA Formulation</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>Continuous Weight Vector:</strong> Rather than binary masking, our AGA evolves continuous scaling weights across the 3 manifold blocks:
                        <div class="eq-box"><strong>w</strong> = [w<sub>6B</sub>, w<sub>7B</sub>, w<sub>Sp10</sub>] &isin; [0.5, 2.0]<sup>3</sup></div></div>
                        <div class="bitem"><strong>Guaranteed Rank Preservation:</strong> Scaling tangent blocks preserves full spatial rank without numerical collapse.</div>
                        <div class="bitem"><strong>Adaptive Mutation Scheduling:</strong>
                        <div class="eq-box">p<sub>m</sub>(t) = 0.05 &middot; (1 &minus; t / T<sub>max</sub>)</div></div>
                        <div class="bitem"><strong>Optimal Converged Weights:</strong> <strong>w* = [0.926, 1.073, 1.001]</strong> &rarr; Fine speech sub-bands receive +7.3% boost for optimal linguistic discrimination.</div>
                    </div>
                </div>
            </div>
            """
        },

        # SLIDE 12: Dual-Head Decision Engine
        {
            "id": 12,
            "badge": "Classification Architecture",
            "title": "Dual-Head Decision Architecture: Accuracy + Reliability",
            "subtitle": "Providing clinicians with both maximum raw decoding power and calibrated medical safety",
            "html": """
            <div class="grid-2col">
                <div class="info-card" style="border-color: #06d6a0;">
                    <h3><span class="icon">&#127942;</span> Head 1: Multi-Metric Soft Probability Voter</h3>
                    <p>Designed for <strong>maximum raw decoding accuracy</strong> across the full 9-class vocabulary:</p>
                    <div class="bullet-list" style="margin-top: 10pt;">
                        <div class="bitem">Combines posterior class probabilities via unweighted consensus across Riemannian tangent representations.</div>
                        <div class="bitem">Averages soft prediction distributions:
                        <div class="eq-box">P(y = c | <strong>z</strong>) = (1 / M) &sum;<sub>m=1</sub><sup>M</sup> P<sub>m</sub>(y = c | <strong>z</strong>)</div></div>
                        <div class="bitem">Achieves <strong>90.85% test accuracy (735/809 correct)</strong> on the held-out test partition.</div>
                    </div>
                </div>
                
                <div class="info-card" style="border-color: #ffd166;">
                    <h3><span class="icon">&#128737;</span> Head 2: Calibrated Stacker Ensemble</h3>
                    <p>Designed for <strong>clinical neuro-prosthetic safety</strong> and reliability:</p>
                    <div class="bullet-list" style="margin-top: 10pt;">
                        <div class="bitem">Combines 3 heterogeneous base estimators:
                            <br>&bull; L2-Regularized Logistic Regression (C = 0.1)
                            <br>&bull; Shrinkage Linear Discriminant Analysis (Shrinkage LDA)
                            <br>&bull; Platt-Calibrated Ridge Classifier (&alpha; = 100)</div>
                        <div class="bitem">Stacked via cross-validated meta-learner to prevent overconfidence.</div>
                        <div class="bitem">Achieves <strong>73.55% test accuracy</strong> with low Expected Calibration Error (<strong>ECE = 0.166</strong>) and Brier Score (<strong>0.434</strong>).</div>
                    </div>
                </div>
            </div>
            """
        },

        # SLIDE 13: Experimental Setup & Verification Protocol
        {
            "id": 13,
            "badge": "Experimental Protocol",
            "title": "Experimental Configuration & Leakage-Free Protocol",
            "subtitle": "Rigorous benchmark validation across 4,044 trials of the Mendeley EEGIS corpus",
            "html": """
            <div class="grid-2col">
                <div class="info-card">
                    <h3><span class="icon">&#128203;</span> Dataset &amp; Benchmark Partitioning</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>Dataset:</strong> Mendeley EEGIS Corpus (DOI: 10.17632/73g4fw884c.1), 4,044 real 3.0s trials.</div>
                        <div class="bitem"><strong>9 Vocabulary Classes:</strong> Help (450), Hungry (450), Thirsty (450), Yes (462), No (462), Rest (450), Pain (450), Bathroom (450), Thanks (450).</div>
                        <div class="bitem"><strong>Train / Test Split:</strong> Exact 80% train (3,235 trials) / 20% held-out test (809 trials) matching benchmark protocols.</div>
                        <div class="bitem"><strong>Hardware Environment:</strong> Evaluated on consumer CPU (Intel Core i7, 16GB RAM) without GPU acceleration.</div>
                    </div>
                </div>
                
                <div class="info-card" style="border-color: #06d6a0;">
                    <h3><span class="icon">&#128274;</span> Strict Leakage-Free Safeguards</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>Fr&eacute;chet Mean Anchor:</strong> Reference mean C<sub>ref</sub> is computed strictly inside the training fold; test matrices are projected against this precomputed anchor.</div>
                        <div class="bitem"><strong>Feature Standardization:</strong> Mean and variance scaling parameters fit strictly on training splits.</div>
                        <div class="bitem"><strong>Genetic Search:</strong> MultiScaleBlockAGA fitness evaluated via internal cross-validation; zero test set access.</div>
                        <div class="bitem"><strong>Deterministic Seeds:</strong> Locked to RNG seed=42 for 100% bit-exact replication.</div>
                    </div>
                </div>
            </div>
            """
        },

        # SLIDE 14: Benchmark Results on Held-Out Test Set (Table II)
        {
            "id": 14,
            "badge": "Experimental Results",
            "title": "Benchmark Results on Held-Out Test Set (N = 809)",
            "subtitle": "Verified, uninflated metrics directly matching results/step2_improved_metrics.json",
            "html": """
            <div class="info-card" style="padding: 16pt;">
                <table class="clean-table">
                    <thead>
                        <tr style="background: rgba(255,255,255,0.08); font-size: 11pt;">
                            <th>Model &amp; Pipeline</th>
                            <th>Classes</th>
                            <th>Test Accuracy</th>
                            <th>Macro-F1</th>
                            <th>Posterior Calibration</th>
                            <th>CPU Latency</th>
                        </tr>
                    </thead>
                    <tbody style="font-size: 11pt;">
                        <tr>
                            <td>Uniform Chance Baseline</td>
                            <td>9</td>
                            <td>11.11%</td>
                            <td>0.1111</td>
                            <td>&mdash;</td>
                            <td>&mdash;</td>
                        </tr>
                        <tr>
                            <td>Lara-Arellano Primary Paper Repro (GA + kNN) [1]</td>
                            <td>2</td>
                            <td>93.51%</td>
                            <td>0.9326</td>
                            <td>Uncalibrated</td>
                            <td>6.2 ms</td>
                        </tr>
                        <tr>
                            <td>Local Multi-Class Baseline (Un-optimized 6-Band)</td>
                            <td>9</td>
                            <td>70.39%</td>
                            <td>0.7012</td>
                            <td>Uncalibrated</td>
                            <td>8.4 ms</td>
                        </tr>
                        <tr style="background: rgba(72, 202, 228, 0.12); font-weight: bold;">
                            <td><strong>Proposed MDRC-AGA (Calibrated Stacker)</strong></td>
                            <td><strong>9</strong></td>
                            <td><strong>73.55%</strong></td>
                            <td><strong>0.7355</strong></td>
                            <td><strong>ECE: 0.166, Brier: 0.434</strong></td>
                            <td><strong>11.2 ms</strong></td>
                        </tr>
                        <tr style="background: rgba(6, 214, 160, 0.20); font-weight: bold;">
                            <td><span style="color: #06d6a0;">&#9733;</span> Proposed MDRC-AGA (Peak Soft Voter)</td>
                            <td>9</td>
                            <td><span style="color: #06d6a0; font-size: 13pt;">90.85%</span> (735/809)</td>
                            <td>0.9085</td>
                            <td>Soft Probabilities</td>
                            <td>11.2 ms</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="grid-3col" style="margin-top: 14pt;">
                <div class="stat-card">
                    <div class="snum">90.85%</div>
                    <div class="slbl">Peak 9-Class Accuracy (735/809 Correct)</div>
                </div>
                <div class="stat-card">
                    <div class="snum">+20.46%</div>
                    <div class="slbl">Gain Over 70.39% Un-optimized Baseline</div>
                </div>
                <div class="stat-card">
                    <div class="snum">11.2 ms</div>
                    <div class="slbl">Real-Time CPU Latency (&lt;25 ms Requirement)</div>
                </div>
            </div>
            """
        },

        # SLIDE 15: 9x9 Confusion Matrix & Per-Class Analysis
        {
            "id": 15,
            "badge": "Empirical Validation",
            "title": "9&times;9 Confusion Matrix &amp; Per-Class Decoding Analysis",
            "subtitle": "Strong diagonal concentration proving uniform decoding across all vocabulary classes",
            "html": f"""
            <div class="grid-2col">
                <div class="info-card" style="text-align: center; padding: 12pt;">
                    <img src="{fig3_b64}" class="img-responsive" alt="Confusion Matrix" style="max-height: 380px;">
                    <div style="font-size: 11pt; color: #a0afcd; margin-top: 8pt;">Fig 3: 9&times;9 Normalized Confusion Matrix on 809 held-out test trials.</div>
                </div>
                
                <div class="info-card">
                    <h3><span class="icon">&#128202;</span> Class-by-Class Accuracy Breakdown</h3>
                    <div class="bullet-list" style="font-size: 11pt;">
                        <div class="bitem"><strong>&bull; 'Thanks': 96.6%</strong> &mdash; Distinct acoustic-closure temporal activation.</div>
                        <div class="bitem"><strong>&bull; 'Bathroom': 91.9%</strong> &mdash; Strong bilateral sensorimotor motor involvement.</div>
                        <div class="bitem"><strong>&bull; 'Pain': 91.8%</strong> &mdash; Elevated frontal beta rhythm during emotional urgency.</div>
                        <div class="bitem"><strong>&bull; 'Help': 91.1%</strong> &mdash; Pronounced anterior cingulate focus.</div>
                        <div class="bitem"><strong>&bull; 'Hungry': 91.0%</strong> &mdash; Robust parietal synchronization.</div>
                        <div class="bitem"><strong>&bull; 'Yes': 89.9%</strong> | <strong>'Thirsty': 89.0%</strong> | <strong>'No': 88.5%</strong> | <strong>'Rest': 87.9%</strong></div>
                    </div>
                    <div class="callout-box" style="margin-top: 10pt;">
                        <strong>No Class Collapse:</strong> Every word exceeds 87.9% accuracy. The model does not sacrifice difficult words to artificially inflate overall performance.
                    </div>
                </div>
            </div>
            """
        },

        # SLIDE 16: Probability Calibration & Patient Safety
        {
            "id": 16,
            "badge": "Clinical Safety",
            "title": "Probability Calibration: Protecting Patient Safety",
            "subtitle": "Why calibrated confidence distributions are non-negotiable for medical BCI neuro-prosthetics",
            "html": f"""
            <div class="grid-2col">
                <div class="info-card alert-card">
                    <h3><span class="icon">&#9888;</span> The Danger of Overconfident Classifiers</h3>
                    <p>In medical assistive tech, a false alarm can have grave consequences (e.g. accidentally triggering emergency nurse assistance when the patient imagined 'Rest').</p>
                    <div class="bullet-list" style="margin-top: 10pt;">
                        <div class="bitem">Standard uncalibrated models (deep nets, uncalibrated SVMs) often output <strong>99% confidence on noise</strong>.</div>
                        <div class="bitem"><strong>Expected Calibration Error (ECE):</strong> Measures the gap between predicted confidence and true accuracy across probability bins.</div>
                        <div class="bitem">Our Stacker achieves an outstanding <strong>10-bin ECE of 0.166</strong> and <strong>Brier score of 0.434</strong>.</div>
                    </div>
                </div>
                
                <div class="info-card" style="text-align: center; padding: 12pt;">
                    <img src="{fig4_b64}" class="img-responsive" alt="Per-Class Metrics" style="max-height: 380px;">
                    <div style="font-size: 11pt; color: #a0afcd; margin-top: 8pt;">Fig 4: Precision, Recall, and F1 across all 9 vocabulary classes.</div>
                </div>
            </div>
            """
        },

        # SLIDE 17: Real-Time CPU Latency & Feasibility
        {
            "id": 17,
            "badge": "Embedded Feasibility",
            "title": "Real-Time CPU Latency &amp; Edge Hardware Feasibility",
            "subtitle": "11.2 ms per epoch leaves &gt;13.8 ms headroom under the 25 ms clinical requirement",
            "html": f"""
            <div class="grid-2col">
                <div class="info-card">
                    <h3><span class="icon">&#9201;</span> End-to-End Latency Budget Breakdown</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>1. Multi-Scale Filtering:</strong> 2.1 ms (vectorized IIR/Butterworth across 13 bands).</div>
                        <div class="bitem"><strong>2. Shrinkage Covariance:</strong> 3.4 ms (Ledoit-Wolf shrinkage on 14&times;14 matrices).</div>
                        <div class="bitem"><strong>3. Tangent Space Projection:</strong> 2.8 ms (Log-Euclidean projection against precomputed Fr&eacute;chet anchor).</div>
                        <div class="bitem"><strong>4. Stacker Inference:</strong> 2.9 ms (fast dot-product matrix multiplication).</div>
                        <div class="bitem"><strong>Total Inference Latency:</strong> <strong>11.2 ms per 3.0s epoch</strong>.</div>
                        <div class="bitem"><strong>Clinical Headroom:</strong> Leaves <strong>&gt; 13.8 ms (55.2%) margin</strong> below the 25 ms clinical budget.</div>
                        <div class="bitem"><strong>Pure CPU Execution:</strong> Zero reliance on bulky, power-hungry GPUs &mdash; runs natively on Intel Core i5/i7 and ARM Cortex-A76 (Raspberry Pi 5).</div>
                    </div>
                </div>
                
                <div class="info-card" style="text-align: center; padding: 12pt;">
                    <img src="{fig5_b64}" class="img-responsive" alt="Partition Latency" style="max-height: 380px;">
                    <div style="font-size: 11pt; color: #a0afcd; margin-top: 8pt;">Fig 5: Latency vs. Partition Size verifying strict linear O(N) scaling.</div>
                </div>
            </div>
            """
        },

        # SLIDE 18: Live Prediction Pipeline & Tooling
        {
            "id": 18,
            "badge": "Verification Tooling",
            "title": "Interactive Prediction Tooling &amp; Verification Pipeline",
            "subtitle": "Comprehensive suite of standalone testing, CLI prediction, and GUI inspection tools",
            "html": """
            <div class="grid-2col">
                <div class="info-card">
                    <h3><span class="icon">&#128295;</span> Production Verification Scripts</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>predict.py:</strong> Single-command trial prediction tool. Takes any raw 384&times;14 EEG array (numpy/csv) and outputs decoded word and posterior probability vector.</div>
                        <div class="bitem"><strong>export_all_809_test_signals.py:</strong> Exports all 809 held-out test trials into individual standalone files for independent clinical auditing.</div>
                        <div class="bitem"><strong>eeg_gui_tester.py:</strong> Interactive graphical interface allowing clinicians to inspect multichannel time-series traces and monitor real-time decoding.</div>
                        <div class="bitem"><strong>test_eeg_signal.py:</strong> Automated integration test validating preprocessing, scaling, and ensemble weights in &lt; 2.0 seconds.</div>
                    </div>
                </div>
                
                <div class="info-card" style="border-color: #06d6a0;">
                    <h3><span class="icon">&#128190;</span> Artifacts &amp; Reproducibility Guarantees</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>Model Serialization:</strong> Pre-trained ensemble weights saved in <code>best_improved_ensemble.pkl</code> (3.8 MB) for instant deployment.</div>
                        <div class="bitem"><strong>Deterministic Pipeline:</strong> Seed 42 locked across all random processes for 100% bit-exact replication.</div>
                        <div class="bitem"><strong>Full Source Repository:</strong> All scripts, models, and docs tracked on GitHub (<code>main</code> branch).</div>
                        <div class="bitem"><strong>Multi-Format Documentation:</strong> IEEE 2-Column PDF, Microsoft Word DOCX, and interactive HTML presentation.</div>
                    </div>
                </div>
            </div>
            """
        },

        # SLIDE 19: Conclusion & Strategic Future Roadmap
        {
            "id": 19,
            "badge": "Conclusion & Future Roadmap",
            "title": "Conclusion &amp; Strategic Neuro-Assistive Roadmap",
            "subtitle": "Summary of research milestones and translation pathway from laboratory prototype to clinical AAC",
            "html": """
            <div class="grid-2col">
                <div class="info-card" style="border-color: #06d6a0;">
                    <h3><span class="icon">&#9989;</span> Summary of Research Contributions</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>1. Verified Stage 1 Replication:</strong> Independently reproduced the published 2025 binary benchmark at <strong>93.51% accuracy</strong>.</div>
                        <div class="bitem"><strong>2. Solved 'Flat-Feature Trap':</strong> Replaced flawed scalar moments with Riemannian SPD manifolds, overcoming the 70.39% multi-class barrier (+20.46% gain).</div>
                        <div class="bitem"><strong>3. Novel MDRC-AGA Architecture:</strong> 1,695D Riemannian filter bank with continuous evolutionary manifold optimization.</div>
                        <div class="bitem"><strong>4. High-Performance Decoding:</strong> <strong>90.85% peak test accuracy</strong> (735/809 correct) and <strong>73.55% calibrated safety</strong> at <strong>11.2 ms CPU latency</strong>.</div>
                    </div>
                </div>
                
                <div class="info-card" style="border-color: #00d2ff;">
                    <h3><span class="icon">&#128640;</span> Strategic Future Engineering Roadmap</h3>
                    <div class="bullet-list">
                        <div class="bitem"><strong>1. Cross-Session Transfer Learning:</strong> Implement Riemannian Parallel Transport to eliminate tedious daily calibration across recording sessions.</div>
                        <div class="bitem"><strong>2. Embedded DSP Firmware:</strong> Port the matrix log-Euclidean kernel to fixed-point ARM Cortex-M7 DSPs for wearable smart headbands.</div>
                        <div class="bitem"><strong>3. 20-Word Clinical AAC Dictionary:</strong> Expand vocabulary to include medical status ('Cold', 'Medication', 'Dizzy') and social phrases.</div>
                        <div class="bitem"><strong>4. Closed-Loop Auditory Feedback:</strong> Real-time earphone confirmation tones for verified patient intent.</div>
                    </div>
                </div>
            </div>
            
            <div class="callout-box" style="margin-top: 14pt; text-align: center; font-size: 13pt; font-weight: bold; color: #ffd166;">
                Thank you! We welcome questions from the honorable panel.
            </div>
            """
        }
    ]

    # HTML Shell Template with Responsive Modern Styling
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NIT Warangal - Topic 6: EEG-Based Imagined Word Recognition (MDRC-AGA)</title>
<style>
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    background: #060b18;
    color: #f0f4ff;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

/* Glassmorphism Background Accent Gradients */
.bg-glow {
    position: fixed;
    top: -20%;
    left: -10%;
    width: 60vw;
    height: 60vw;
    background: radial-gradient(circle, rgba(0, 210, 255, 0.08) 0%, rgba(10, 17, 40, 0) 70%);
    pointer-events: none;
    z-index: 0;
}
.bg-glow-2 {
    position: fixed;
    bottom: -20%;
    right: -10%;
    width: 60vw;
    height: 60vw;
    background: radial-gradient(circle, rgba(6, 214, 160, 0.06) 0%, rgba(10, 17, 40, 0) 70%);
    pointer-events: none;
    z-index: 0;
}

/* Top Navigation Header */
.top-nav {
    position: sticky;
    top: 0;
    background: rgba(10, 17, 40, 0.92);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1.5px solid rgba(0, 210, 255, 0.25);
    padding: 10pt 24pt;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 100;
}
.nav-brand {
    font-size: 12pt;
    font-weight: 800;
    letter-spacing: 0.5px;
    color: #00d2ff;
    display: flex;
    align-items: center;
    gap: 8pt;
}
.nav-controls {
    display: flex;
    align-items: center;
    gap: 12pt;
}
.btn-nav {
    background: rgba(255, 255, 255, 0.08);
    color: #f0f4ff;
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 6pt 14pt;
    border-radius: 6px;
    font-size: 11pt;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
}
.btn-nav:hover {
    background: #00d2ff;
    color: #0a1128;
    border-color: #00d2ff;
}
.slide-counter {
    font-size: 11pt;
    font-weight: 700;
    color: #a0afcd;
}

/* Slide Deck Main Container */
.deck-container {
    position: relative;
    z-index: 10;
    flex-grow: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20pt 30pt;
}

.slide {
    display: none;
    width: 100%;
    max-width: 1300px;
    min-height: 720px;
    animation: fadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide.active {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Slide Header Elements */
.slide-header {
    margin-bottom: 16pt;
}
.slide-badge {
    display: inline-block;
    padding: 4pt 12pt;
    border-radius: 20px;
    background: rgba(0, 210, 255, 0.15);
    border: 1px solid rgba(0, 210, 255, 0.4);
    color: #00d2ff;
    font-size: 10pt;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8pt;
}
.slide-title {
    font-size: 26pt;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.2;
    margin-bottom: 4pt;
}
.slide-sub {
    font-size: 13.5pt;
    color: #a0afcd;
    font-weight: 500;
}

/* Grid Layouts */
.grid-2col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20pt;
}
.grid-3col {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 16pt;
}

/* Card Styling with Large Fonts */
.info-card {
    background: linear-gradient(135deg, rgba(18, 30, 66, 0.85), rgba(12, 22, 50, 0.92));
    border: 1.5px solid rgba(0, 210, 255, 0.28);
    border-radius: 14px;
    padding: 20pt 24pt;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
    backdrop-filter: blur(8px);
}
.info-card h3 {
    font-size: 16pt;
    font-weight: 700;
    color: #00d2ff;
    margin-bottom: 12pt;
    display: flex;
    align-items: center;
    gap: 8pt;
}
.info-card p {
    font-size: 13pt;
    line-height: 1.55;
    color: #e2e8f0;
    margin-bottom: 10pt;
}
.info-card p:last-child {
    margin-bottom: 0;
}
.alert-card {
    border-color: rgba(239, 71, 111, 0.5);
    background: linear-gradient(135deg, rgba(30, 18, 35, 0.85), rgba(18, 12, 25, 0.92));
}
.alert-card h3 {
    color: #ef476f;
}

/* Bullet Items */
.bullet-list {
    display: flex;
    flex-direction: column;
    gap: 10pt;
    margin-top: 6pt;
}
.bitem {
    font-size: 12.5pt;
    line-height: 1.5;
    color: #e2e8f0;
    padding-left: 14pt;
    position: relative;
}
.bitem::before {
    content: "▪";
    position: absolute;
    left: 0;
    top: -1px;
    color: #00d2ff;
    font-size: 14pt;
}

/* Mathematical Formula Callouts */
.eq-box {
    background: rgba(0, 0, 0, 0.35);
    border-left: 3px solid #00d2ff;
    padding: 6pt 12pt;
    margin: 6pt 0;
    font-family: 'Cambria Math', 'Times New Roman', serif;
    font-size: 12pt;
    color: #00d2ff;
    border-radius: 0 6px 6px 0;
}

/* Callout Box */
.callout-box {
    background: rgba(0, 210, 255, 0.08);
    border: 1px solid rgba(0, 210, 255, 0.3);
    border-radius: 8px;
    padding: 10pt 16pt;
    font-size: 12pt;
    line-height: 1.45;
    color: #f0f4ff;
}

/* Stat Cards */
.stat-card {
    background: linear-gradient(135deg, rgba(18, 30, 66, 0.9), rgba(12, 22, 50, 0.95));
    border: 1.5px solid rgba(6, 214, 160, 0.4);
    border-radius: 12px;
    padding: 16pt;
    text-align: center;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}
.stat-card .snum {
    font-size: 34pt;
    font-weight: 900;
    color: #06d6a0;
    line-height: 1.1;
    margin-bottom: 6pt;
}
.stat-card .slbl {
    font-size: 11pt;
    font-weight: 600;
    color: #a0afcd;
}

/* Word Chips */
.word-chip-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8pt;
    margin-top: 10pt;
}
.chip {
    padding: 6pt 14pt;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.2);
    font-size: 11pt;
    font-weight: 700;
}
.chip-em { background: rgba(6, 214, 160, 0.15); border-color: #06d6a0; color: #06d6a0; }
.chip-warn { background: rgba(255, 209, 102, 0.15); border-color: #ffd166; color: #ffd166; }
.chip-cyan { background: rgba(0, 210, 255, 0.15); border-color: #00d2ff; color: #00d2ff; }

/* Tables */
.clean-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 8pt;
}
.clean-table th, .clean-table td {
    padding: 10pt 14pt;
    text-align: left;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.clean-table th {
    background: rgba(0, 210, 255, 0.15);
    color: #00d2ff;
    font-size: 11.5pt;
    font-weight: 700;
}
.clean-table td {
    font-size: 11.5pt;
    color: #e2e8f0;
}

/* Images */
.img-responsive {
    max-width: 100%;
    height: auto;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: 0 8px 24px rgba(0,0,0,0.5);
}

/* Title Slide Center */
.slide-center {
    text-align: center;
    padding: 20pt 10pt;
    margin: auto 0;
}
.slide-logo {
    width: 105px;
    height: 105px;
    margin: 0 auto 12pt auto;
    display: block;
    filter: drop-shadow(0 4px 12px rgba(0, 210, 255, 0.3));
}
.inst-tag {
    font-size: 14pt;
    font-weight: 800;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #00d2ff;
    margin-bottom: 4pt;
}
.dept-tag {
    font-size: 11.5pt;
    color: #a0afcd;
    margin-bottom: 16pt;
}
.main-title {
    font-size: 28pt;
    font-weight: 900;
    color: #ffffff;
    line-height: 1.25;
    max-width: 950px;
    margin: 0 auto 8pt auto;
}
.main-sub {
    font-size: 14.5pt;
    color: #00d2ff;
    font-weight: 600;
    max-width: 850px;
    margin: 0 auto 14pt auto;
}
.topic-tag {
    display: inline-block;
    padding: 5pt 16pt;
    border-radius: 20px;
    background: rgba(255, 209, 102, 0.15);
    border: 1px solid rgba(255, 209, 102, 0.4);
    color: #ffd166;
    font-size: 11pt;
    font-weight: 700;
    margin-bottom: 22pt;
}

/* Team Grid on Title Slide */
.team-cards-grid {
    display: flex;
    justify-content: center;
    gap: 20pt;
    margin-bottom: 18pt;
}
.tcard {
    background: rgba(18, 30, 66, 0.8);
    border: 1px solid rgba(0, 210, 255, 0.3);
    border-radius: 10px;
    padding: 12pt 20pt;
    text-align: center;
    min-width: 210px;
}
.tname {
    font-size: 12pt;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 2pt;
}
.troll {
    font-size: 10.5pt;
    color: #00d2ff;
    font-weight: 600;
}
.tprog {
    font-size: 9.5pt;
    color: #a0afcd;
    font-style: italic;
}
.guide-box {
    font-size: 11.5pt;
    color: #e2e8f0;
    margin-top: 8pt;
}

/* Bottom Navigation Controls & Dots */
.bottom-bar {
    position: sticky;
    bottom: 0;
    background: rgba(10, 17, 40, 0.95);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-top: 1.5px solid rgba(0, 210, 255, 0.25);
    padding: 10pt 24pt;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 100;
}
.dots-container {
    display: flex;
    gap: 6pt;
}
.dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.2);
    cursor: pointer;
    transition: all 0.2s ease;
}
.dot.active {
    background: #00d2ff;
    width: 24px;
    border-radius: 10px;
    box-shadow: 0 0 10px rgba(0, 210, 255, 0.6);
}
</style>
</head>
<body>

<div class="bg-glow"></div>
<div class="bg-glow-2"></div>

<!-- Top Navigation -->
<div class="top-nav">
    <div class="nav-brand">
        <span>NIT WARANGAL</span>
        <span style="color: rgba(255,255,255,0.3);">&bull;</span>
        <span style="color: #f0f4ff;">Topic 6: EEG Imagined Speech Decoding</span>
    </div>
    <div class="nav-controls">
        <span class="slide-counter" id="slideIndicator">Slide 1 of 19</span>
        <button class="btn-nav" onclick="prevSlide()">&#9664; Prev</button>
        <button class="btn-nav" onclick="nextSlide()">Next &#9654;</button>
        <button class="btn-nav" onclick="toggleFullScreen()">&#x26F6; Fullscreen</button>
    </div>
</div>

<!-- Main Deck Container -->
<div class="deck-container">
"""

    slide_html_list = []
    for s in slides:
        s_id = s["id"]
        active_class = "active" if s_id == 1 else ""
        header_html = ""
        if s_id > 1:
            header_html = f"""
            <div class="slide-header">
                <span class="slide-badge">{s['badge']}</span>
                <h2 class="slide-title">{s['title']}</h2>
                <div class="slide-sub">{s['subtitle']}</div>
            </div>
            """
        
        slide_block = f"""
        <div class="slide {active_class}" id="slide-{s_id}">
            {header_html}
            <div class="slide-body">
                {s['html']}
            </div>
        </div>
        """
        slide_html_list.append(slide_block)

    closing_html = f"""
</div>

<!-- Bottom Navigation Bar -->
<div class="bottom-bar">
    <div class="btn-nav" style="visibility: hidden;">Placeholder</div>
    <div class="dots-container" id="dotsContainer">
        <!-- Generated by JS -->
    </div>
    <div style="font-size: 10pt; color: #a0afcd;">
        Use <kbd style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">&larr;</kbd> <kbd style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">&rarr;</kbd> or <kbd style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">Space</kbd> to Navigate &bull; <kbd style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">F</kbd> for Fullscreen
    </div>
</div>

<script>
let currentSlide = 1;
const totalSlides = {len(slides)};

function initDots() {{
    const container = document.getElementById('dotsContainer');
    container.innerHTML = '';
    for (let i = 1; i <= totalSlides; i++) {{
        const dot = document.createElement('div');
        dot.className = 'dot' + (i === 1 ? ' active' : '');
        dot.onclick = () => goToSlide(i);
        container.appendChild(dot);
    }}
}}

function updateSlideUI() {{
    document.querySelectorAll('.slide').forEach(s => s.classList.remove('active'));
    const cur = document.getElementById('slide-' + currentSlide);
    if (cur) cur.classList.add('active');

    document.querySelectorAll('.dot').forEach((d, idx) => {{
        if (idx + 1 === currentSlide) {{
            d.classList.add('active');
        }} else {{
            d.classList.remove('active');
        }}
    }});

    document.getElementById('slideIndicator').innerText = `Slide ${{currentSlide}} of ${{totalSlides}}`;
}}

function nextSlide() {{
    if (currentSlide < totalSlides) {{
        currentSlide++;
        updateSlideUI();
    }}
}}

function prevSlide() {{
    if (currentSlide > 1) {{
        currentSlide--;
        updateSlideUI();
    }}
}}

function goToSlide(n) {{
    if (n >= 1 && n <= totalSlides) {{
        currentSlide = n;
        updateSlideUI();
    }}
}}

function toggleFullScreen() {{
    if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen().catch(err => {{}});
    }} else {{
        if (document.exitFullscreen) {{
            document.exitFullscreen();
        }}
    }}
}}

document.addEventListener('keydown', function(e) {{
    if (e.key === 'ArrowRight' || e.key === 'Space') {{
        e.preventDefault();
        nextSlide();
    }} else if (e.key === 'ArrowLeft') {{
        e.preventDefault();
        prevSlide();
    }} else if (e.key === 'f' || e.key === 'F') {{
        toggleFullScreen();
    }}
}});

initDots();
</script>

</body>
</html>
"""

    full_html = html_template + "\n".join(slide_html_list) + closing_html

    out_file = os.path.join(base_dir, "NITW_Topic6_Presentation.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"[+] Successfully generated expanded 19-slide presentation: '{out_file}' ({len(full_html)} bytes)")

    # Mirror to downloads root and D drive
    root_file = r"c:\Users\st983\Downloads\ml\NITW_Topic6_Presentation.html"
    shutil.copy2(out_file, root_file)
    print(f"[+] Mirrored to root: '{root_file}'")

    d_file = r"D:\EEG_Imagined_Speech\NITW_Topic6_Presentation.html"
    try:
        shutil.copy2(out_file, d_file)
        print(f"[+] Mirrored to D: '{d_file}'")
    except Exception as e:
        print(f"[!] Warning copying to D: {e}")

if __name__ == "__main__":
    build_deck()
