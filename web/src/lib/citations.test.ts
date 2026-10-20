import { citedPassages, formatSource, linkCitations, parseCitationGroup } from "./citations";

describe("parseCitationGroup", () => {
  it("parses single numbers, lists and ranges", () => {
    expect(parseCitationGroup("2", 5)).toEqual([2]);
    expect(parseCitationGroup("1, 3", 5)).toEqual([1, 3]);
    expect(parseCitationGroup("2-4", 5)).toEqual([2, 3, 4]);
    expect(parseCitationGroup("1, 3–5", 5)).toEqual([1, 3, 4, 5]);
  });

  it("drops numbers outside the retrieved passages", () => {
    expect(parseCitationGroup("0, 2, 9", 5)).toEqual([2]);
  });
});

describe("citedPassages", () => {
  it("collects every cited passage in the answer", () => {
    const answer = "p-tau217 rises early [1]. APOE4 raises risk [2, 4]. See also [7].";
    expect([...citedPassages(answer, 5)].sort()).toEqual([1, 2, 4]);
  });

  it("ignores markdown links and plain brackets", () => {
    expect(citedPassages("[see here](http://x) and [note]", 5).size).toBe(0);
  });
});

describe("linkCitations", () => {
  it("turns markers into anchor links", () => {
    expect(linkCitations("Claim [1, 2].", 5)).toBe("Claim [[1]](#cite-1)[[2]](#cite-2).");
  });

  it("leaves markers that point at no passage", () => {
    expect(linkCitations("Claim [9].", 5)).toBe("Claim [9].");
  });
});

describe("formatSource", () => {
  it("formats PubMed and PDF sources", () => {
    expect(formatSource("pubmed:123")).toBe("PMID 123");
    expect(formatSource("pdf:review.pdf")).toBe("review.pdf");
    expect(formatSource("other")).toBe("other");
  });
});
