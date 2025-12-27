import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Search, Heart, Edit, Plus, RefreshCcw, Edit3, ListMusic } from 'lucide-react';
import TagEditor from '@/components/TagEditor';
import { api } from '@/lib/api';
import { useGenerateAllM3U } from '@/hooks/useGenerateAllM3U';

interface Song {
  Title: string;
  Artist: string;
  Album: string;
  MainFolder: string;
  FilePath: string;
  Genre: string[];
  Language: string;
  Favorite: string;
  Cover: string;
  SortTitle?: string;
  SortArtist?: string;
  SortAlbum?: string;
  SortAlbumArtist?: string;
  SortComposer?: string;
  SortPerformer?: string;
  AlbumArtist?: string;
  Composer?: string;
  Performer?: string;
  DiscNumber?: string;
  DiscTotal?: string;
  Lyrics?: string;
  Comment?: string;
  JfId?: string;
  JellyfinAddTime?: string;
  ReplayGainTrackGain?: string;
  ReplayGainTrackPeak?: string;
  ReplayGainAlbumGain?: string;
  ReplayGainAlbumPeak?: string;
}

interface ApiResponse {
  audio_files: Song[];
  pagination: {
    current_page: number;
    page_size: number;
    total_count: number;
    total_pages: number;
    has_previous: boolean;
    has_next: boolean;
  };
  allow_folders: string[];
  supported_languages: { [key: string]: string };
}

export default function Home() {
  const navigate = useNavigate();
  const [songs, setSongs] = useState<Song[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTitle, setSearchTitle] = useState('');
  const [selectedFolder, setSelectedFolder] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState('');
  const [showFavorites, setShowFavorites] = useState(false);
  const [allowFolders, setAllowFolders] = useState<string[]>([]);
  const [supportedLanguages, setSupportedLanguages] = useState<{ [key: string]: string }>({});
  const [pagination, setPagination] = useState({
    current_page: 1,
    total_pages: 1,
    total_count: 0
  });
  const [editingSong, setEditingSong] = useState<Song | null>(null);

  // 使用批量生成 M3U 的 hook
  const { generatingAll, handleGenerateAllM3U } = useGenerateAllM3U();

  const fetchSongs = async (page = 1) => {
    setLoading(true);
    try {
      const params: Record<string, string> = {
        p: page.toString(),
        details: 'true'
      };

      if (searchTitle) params.filterTitle = searchTitle;
      if (selectedFolder) params.filterFolder = selectedFolder;
      if (selectedLanguage) params.filterLanguage = selectedLanguage;
      if (showFavorites) params.filterFavorite = 'true';

      const data: ApiResponse = await api.get('audios', params);

      setSongs(data.audio_files);
      setAllowFolders(data.allow_folders);
      setSupportedLanguages(data.supported_languages || {});

      setPagination({
        current_page: data.pagination.current_page,
        total_pages: data.pagination.total_pages,
        total_count: data.pagination.total_count
      });
    } catch (error) {
      console.error('Failed to fetch songs:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSongs();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchSongs(1);
  }, [showFavorites]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = () => {
    fetchSongs(1);
  };

  const handlePageChange = (page: number) => {
    fetchSongs(page);
  };

  const handleSaveTags = async (song: Song) => {
    try {
      await api.put('audios/update', {
        path: song.FilePath,
        tags: [{
          title: song.Title,
          artist: song.Artist,
          album: song.Album,
          albumartist: song.AlbumArtist || '',
          composer: song.Composer || '',
          performer: song.Performer || '',
          titlesort: song.SortTitle,
          artistsort: song.SortArtist,
          albumsort: song.SortAlbum,
          albumartistsort: song.SortAlbumArtist || '',
          composersort: song.SortComposer || '',
          performersort: song.SortPerformer || '',
          discnumber: song.DiscNumber || '',
          disctotal: song.DiscTotal || '',
          genre: song.Genre,
          language: song.Language,
          favorite: song.Favorite,
          lyrics: song.Lyrics || '',
          comment: song.Comment || '',
          jfid: song.JfId || '',
          jellyfin_add_time: song.JellyfinAddTime || '',
          replaygain_track_gain: song.ReplayGainTrackGain || '',
          replaygain_track_peak: song.ReplayGainTrackPeak || '',
          replaygain_album_gain: song.ReplayGainAlbumGain || '',
          replaygain_album_peak: song.ReplayGainAlbumPeak || ''
        }]
      });

      fetchSongs(pagination.current_page);
      setEditingSong(null);
    } catch (error) {
      console.error('Error saving tags:', error);
    }
  };

  return (
    <div className="mx-auto px-8 py-4">
      <div className="mb-8">
        <div className="flex flex-col md:flex-row items-start gap-4 mt-4 mb-6 ">
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            歌曲管理
          </h1>
          <div className="flex-1 flex gap-2 flex-wrap items-start justify-start md:justify-end">
            <Button
              variant='outline'
              onClick={handleGenerateAllM3U}
              disabled={generatingAll}
              className="flex items-center gap-2"
            >
              {generatingAll ? (
                <RefreshCcw className="w-4 h-4 animate-spin" />
              ) : (
                <ListMusic className="w-4 h-4" />
              )}
              {generatingAll ? '生成中...' : '生成 M3U'}
            </Button>
            <Button
              className="flex items-center gap-2"
              onClick={() => navigate('/new')}
            >
              <Plus className="h-4 w-4" />
              新增歌曲
            </Button>
          </div>
        </div>

        {/* 搜尋和篩選區域 */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              搜尋和篩選
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
              <div className="md:col-span-2">
                <Input
                  placeholder="搜尋歌曲標題..."
                  value={searchTitle}
                  onChange={(e) => setSearchTitle(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                />
              </div>
              <Select
                value={selectedFolder || 'ALL'}
                onValueChange={(value) => setSelectedFolder(value === 'ALL' ? '' : value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="所有資料夾" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">所有資料夾</SelectItem>
                  {allowFolders.map(folder => (
                    <SelectItem key={folder} value={folder}>{folder}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select
                value={selectedLanguage || 'ALL'}
                onValueChange={(value) => setSelectedLanguage(value === 'ALL' ? '' : value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="所有語言" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">所有語言</SelectItem>
                  {Object.entries(supportedLanguages).map(([code, name]) => (
                    <SelectItem key={code} value={code}>{name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant={showFavorites ? 'default' : 'outline'}
                onClick={() => {
                  const newShowFavorites = !showFavorites;
                  setShowFavorites(newShowFavorites);
                }}
                className="flex items-center gap-2"
              >
                <Heart className={`h-4 w-4 ${showFavorites ? 'fill-current' : ''}`} />
                {showFavorites ? '顯示全部' : '只顯示最愛'}
              </Button>
              <Button onClick={handleSearch} className="flex items-center gap-2">
                <Search className="h-4 w-4" />
                搜尋
              </Button>
            </div>
            <div className="mt-4 flex items-center gap-4">
              {/* 統計資訊 */}
              <div className="text-sm text-muted-foreground">
                共找到 {pagination.total_count} 首歌曲，第 {pagination.current_page} 頁 / 共 {pagination.total_pages} 頁
              </div>
            </div>
          </CardContent>
        </Card>


      </div>

      {/* 歌曲清單 */}
      {loading ? (
        <div className="text-center py-8">載入中...</div>
      ) : (
        <>
          <div className="bg-white rounded-2xl border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-500 tracking-wider max-w-[200px] min-w-[100px]">
                      標題
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500 tracking-wider max-w-[200px] min-w-[100px]">
                      藝術家
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500 tracking-wider max-w-[200px] min-w-[100px]">
                      專輯
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500 tracking-wider max-w-[200px] min-w-[100px]">
                      資料夾
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500 tracking-wider max-w-[200px] min-w-[100px]">
                      流派
                    </th>
                    <th className="px-4 py-3 text-center text-nowrap font-medium text-gray-500 tracking-wider max-w-[80px] min-w-[40px]">
                      語言
                    </th>
                    <th className="px-4 py-3 text-center text-nowrap font-medium text-gray-500 tracking-wider max-w-[80px] min-w-[40px]">
                      最愛
                    </th>
                    <th className="px-4 py-3 text-center font-medium text-gray-500 tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {songs.map((song, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-4 py-3 max-w-[200px] min-w-[100px]">
                        <div className="font-medium text-foreground truncate">
                          {song.Title || '未知標題'}
                        </div>
                        <div className="text-sm text-muted-foreground truncate">
                          {song.SortTitle || '未知標題'}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[200px] min-w-[100px]">
                        <div className="font-medium text-foreground truncate">
                          {song.Artist || '未知藝術家'}
                        </div>
                        <div className="text-sm text-muted-foreground truncate">
                          {song.SortArtist || '未知藝術家'}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[200px] min-w-[100px]">
                        <div className="font-medium text-foreground truncate">
                          {song.Album || '未知專輯'}
                        </div>
                        <div className="text-sm text-muted-foreground truncate">
                          {song.SortAlbum || '未知專輯'}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[200px] min-w-[100px]">
                        <div className="font-medium text-foreground truncate">
                          <span className="inline-block px-2 py-0.5 mb-2 text-sm bg-muted-foreground text-white rounded-full">
                            {song.MainFolder}
                          </span>
                        </div>
                        <div className="text-sm text-muted-foreground truncate">
                          {song.FilePath || '未知路徑'}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[320px] min-w-[200px]">
                        <div className="text-sm flex flex-wrap gap-2 w-full">
                          {song.Genre.length > 0 ? (
                            song.Genre.map((genre, index) => (
                              <span key={index} className="inline-block px-2 py-1 text-sm bg-gray-100 text-foreground rounded-full">
                                {genre}
                              </span>
                            ))
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center max-w-[80px] min-w-[40px]">
                        <div className="text-sm text-foreground max-w-[100px] min-w-[40px]">
                          {song.Language || '-'}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[80px] min-w-[40px]">
                        {song.Favorite === 'True' ? (
                          <Heart className="h-4 w-4 text-red-500 fill-current mx-auto" />
                        ) : (
                          <div className="h-4 w-4 mx-auto"></div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <Button
                          variant="clear"
                          size="sm"
                          className="flex items-center gap-1 mx-auto"
                          onClick={() => setEditingSong(song)}
                        >
                          <Edit3 className="size-5" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 分頁 */}
          {pagination.total_pages > 1 && (
            <div className="flex justify-center items-center gap-2 mt-8">
              <Button
                variant="outline"
                disabled={pagination.current_page === 1}
                onClick={() => handlePageChange(pagination.current_page - 1)}
              >
                上一頁
              </Button>
              <span className="px-4 py-2 text-sm text-muted-foreground">
                {pagination.current_page} / {pagination.total_pages}
              </span>
              <Button
                variant="outline"
                disabled={pagination.current_page === pagination.total_pages}
                onClick={() => handlePageChange(pagination.current_page + 1)}
              >
                下一頁
              </Button>
            </div>
          )}
        </>
      )}

      <TagEditor
        song={editingSong}
        onClose={() => setEditingSong(null)}
        onSave={handleSaveTags}
      />
    </div>
  );
}
