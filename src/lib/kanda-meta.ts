export interface KandaEditorialMeta {
  devaNum: string;
  subtitle: string;
  chapterRangeNote: string;
}

export const KANDA_META: Record<string, KandaEditorialMeta> = {
  '01-bala': {
    devaNum: '१',
    subtitle: 'Origins, Viśvāmitra’s yajña, and the marriage of Rāma and Sītā',
    chapterRangeNote: 'Book of Youth',
  },
  '02-ayodhya': {
    devaNum: '२',
    subtitle: 'The halted consecration, exile to Chitrakūṭa, and Bharata’s devotion',
    chapterRangeNote: 'Book of Ayodhyā',
  },
  '03-aranya': {
    devaNum: '३',
    subtitle: 'Life in Daṇḍaka forest, Śūrpaṇakhā, and the abduction of Sītā',
    chapterRangeNote: 'Book of the Forest',
  },
  '04-kishkindha': {
    devaNum: '४',
    subtitle: 'Alliance with Sugrīva, Vāli’s fall, and the search party sent south',
    chapterRangeNote: 'Book of Kiṣkindhā',
  },
  '05-sundara': {
    devaNum: '५',
    subtitle: 'Hanumān’s leap across the ocean, Aśoka grove, and the burning of Laṅkā',
    chapterRangeNote: 'Book of Beauty',
  },
  '06-yuddha': {
    devaNum: '६',
    subtitle: 'Building the bridge, the siege of Laṅkā, Rāvaṇa’s defeat, and coronation',
    chapterRangeNote: 'Book of War',
  },
  '07-uttara': {
    devaNum: '७',
    subtitle: 'Rāvaṇa’s lineage, Rāma’s reign, Lava and Kuśa, and the final departure',
    chapterRangeNote: 'The Later Book',
  },
};
