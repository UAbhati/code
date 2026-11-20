class Solution {
public:
    int countComponents(int n, vector<vector<int>>& edges) {
        vector<int> parent(n), rank(n,0);
        iota(parent.begin(), parent.end(), 0);

        function<int(int)> find = [&](int x) -> int {
            if (parent[x] != x) {
                parent[x] = find(parent[x]);
            }
            return parent[x];
        }
        auto union = [&](int x, int y) {
            int px = find(x);
            int py = find(y);

            if(px == py) return false;
            if(rank[px] < rank[py]) {
                swap(px, py);
            }
            parent[py] = px;
            if(rank[px] == rank[py]) {
                rank[px]++;
            }
            return true;
        }

        int components = n;
        for(auto& edge : edges) {
            if(union(edge[0], edge[1])) {
                components--;
            }
        }
        return components;
    }
};