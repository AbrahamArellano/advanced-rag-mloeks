from fpdf import FPDF
pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
content = """SkyWing Airways: Your Ultimate Travel Partner
SkyWing Airways is dedicated to redefining air travel by offering exceptional comfort, top-tier safety, and world-class service. As a leading airline, we now serve over 160 destinations globally, expanding our reach to provide more travel options and seamless experiences for our valued customers.
Our state-of-the-art fleet has been updated to feature the latest aircraft models, ensuring every journey is smooth, efficient, and eco-friendly. The SkyWing fleet now includes the Boeing 787 Dreamliner, Airbus A350, Boeing 777X, and the Airbus A320neo, a new eco-friendly upgrade for short-haul routes.
With our expanded route network, SkyWing Airways now serves 40 cities in North America, 50 in Europe, 35 in Asia, 18 in South America, 22 in Africa, and 6 in Oceania, offering our passengers even more travel choices across the world.
We've also enhanced our classes of service to deliver unmatched comfort and luxury. Economy class now offers a 34" seat pitch, Wi-Fi, and an improved meal service. Premium Economy has a 40" seat pitch, expanded meal options, and priority boarding. Business Class features lie-flat seats, chef-curated meals, and access to luxury lounges, while First Class provides ultra-private suites, personal butler service, à la carte dining, and even spa treatments.
SkyWing's Premium Rewards Program has been upgraded to offer even more benefits, including free flights, seat upgrades, and exclusive VIP experiences. Our tier structure includes Blue (entry level), Silver (30,000 miles per year), Gold (60,000 miles per year), Platinum (120,000 miles per year), and the newly introduced Diamond tier (150,000 miles per year), offering the highest level of exclusive perks.
We've also updated our baggage policy to better accommodate our passengers. Economy class now allows two checked bags (up from one), each with a maximum weight of 25kg. Premium Economy passengers can check three bags of up to 32kg each, while Business and First Class passengers can check four bags, each with a maximum weight of 48kg.
As part of our commitment to sustainability, SkyWing Airways is focused on reducing our carbon footprint. We've upgraded our fleet with eco-friendly aircraft and are investing in sustainable aviation fuel. Our goal is to achieve carbon neutrality by 2040, reflecting our commitment to a greener future.
For the latest offers, travel plans, and more, visit us at www.skywingairways.com. SkyWing Airways is committed to making your journey as enjoyable and comfortable as possible, from booking to your destination."""
pdf.multi_cell(0, 10, content)
pdf.output("skywingairways.pdf")
print("PDF created successfully!")
