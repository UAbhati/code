class Solution {
    public:
        int shortestPathBinaryMatrix(vector<vector<int>>& grid) {
            int n = grid.size();
            queue<pair<int,int>> q;
            if(grid[0][0] != 0 || grid[n-1][n-1] != 0) return -1;
            if(n == 1) return 1;

            q.push({0,0});
            int level = 1;
            vector<vector<bool>> visited(n,vector<bool>(n,false));
            visited[0][0] = true;
            int dx[] = {1,-1,0,0,1,-1,1,-1};
            int dy[] = {1,-1,1,-1,0,0,-1,1};
            while(!q.empty()) {
                int t = q.size();
                while(t--){
                    auto [x, y] = q.front();
                    q.pop();
                    for(int k=0;k<8;k++) {
                        int nx = x + dx[k];
                        int ny = y + dy[k];
                        if(nx >=0 && nx <n && ny >=0 && ny <n && grid[nx][ny] == 0 && !visited[nx][ny]) {
                            if(nx == n-1 && ny == n-1) return level+1;
                            q.push({nx, ny});
                            visited[nx][ny] = true;
                        }
                    }
                }
                level++;
            }
            return -1;
        }
    };