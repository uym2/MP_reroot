from Tree_extend import *
from quadprog_example import *

EPSILON = 1e-5

class RTT_Tree(Tree_extend):
    # supportive base class to implement VAR-reroot, hence the name
    def __init__(self,smplTimes, solver="AS", ddpTree=None, tree_file=None,schema="newick"):
        super(RTT_Tree, self).__init__(ddpTree, tree_file, schema)
        self.smplTimes = smplTimes
        self.solver = solver
        self.reset()

    def reset(self):
        self.RTT = None
        self.opt_root = self.ddpTree.root
        self.opt_x = 0
        self.opt_mu = 0

    def Node_init(self, node, nleaf=1, SDI=0, SD=0, var=-1, ST=0, SDT=0, SSD=0):
        node.SDI = SDI
        node.SD = SD
        node.nleaf = nleaf
        node.ST = ST
        node.SDT = SDT
        node.SSD = SSD

    def Opt_function(self, node, SST, deltaT, deltaD, SDT, SSD, solver = "AS"):
    # solver can be "AS" (active-set) or "QP" (quad-prog)
        n = self.total_leaves
        a, b, c, d, e, f = n, SST, (-2 * deltaT), (2 * deltaD), (-2 * SDT), SSD
        
        # find global mu_star and x_star
        mu_star = (SDT - deltaT * deltaD / n) / (SST - deltaT * deltaT / n)
        x_star = (deltaT * mu_star - deltaD) / n
        
        if x_star >= 0 and x_star <= node.edge_length and mu_star >= 0:
            curr_RTT = a * x_star * x_star + b * mu_star * mu_star + c * x_star * mu_star + d * x_star + e * mu_star + f
        elif solver == "QP":
            # use quadprog to compute mu_star and x_star
            P = array([[a,c/2.],[c/2,b]])
            q = array([d/2., e/2])
            G = array([[-1., 0.], [0., -1.], [1., 0.]])
            h = array([0., 0., node.edge_length]).reshape((3,))
            solution = quadprog_solve_qp(P, q, G, h)
            x_star = solution[0]
            mu_star = solution[1]
            curr_RTT = a * x_star * x_star + b * mu_star * mu_star + c * x_star * mu_star + d * x_star + e * mu_star + f
            #print(solution)
            # ^ x,m are different when using quadprog, but rooted tree is same for some
        else:
            # use active_set technique to compute mu_star and x_star
            if x_star < 0:
                x_star = 0
                mu_star = -e / (2 * b)
                if mu_star < 0:
                    mu_star = 0
            elif x_star > node.edge_length:
                x_star = node.edge_length
                mu_star = -(e + c * node.edge_length) / (2 * b)
                if mu_star < 0:
                    mu_star = 0
            elif mu_star < 0:
                mu_star = 0
                x_star = -d / (2 * a)
                if x_star < 0:
                    x_star = 0
                elif x_star > node.edge_length:
                    x_star = node.edge_length
            curr_RTT = a * x_star * x_star + b * mu_star * mu_star + c * x_star * mu_star + d * x_star + e * mu_star + f
        
        if self.RTT is None or (curr_RTT - self.RTT < -EPSILON):
            self.RTT = curr_RTT
            self.opt_root = node
            self.opt_x = node.edge_length - x_star
            self.opt_mu = mu_star

    def bUp_update(self, node):
        if node.is_leaf():
            node.nleaf = 1
            node.SDI = 0
            node.ST = self.smplTimes[node.label]
        else:
            node.nleaf = 0
            node.SDI = 0
            node.ST = 0
            for child in node.child_nodes():
                node.nleaf += child.nleaf
                node.SDI += child.SDI + child.nleaf * child.edge_length
                node.ST += child.ST

    def Update_var(self, child, node, edge_length):
        SST = self.SST
        deltaT = self.ddpTree.root.ST - 2 * child.ST
        deltaD = -2 * child.nleaf * edge_length - 2 * child.SDI + node.SD
        SDT = node.SDT
        SSD = node.SSD
        return SST, deltaT, deltaD, SDT, SSD

    def tDown_update(self, node, opt_function):
        for child in node.child_nodes():
            child.SD = node.SD + (self.total_leaves - 2 * child.nleaf) * child.edge_length
            child.SDT = node.SDT + child.edge_length * (self.ddpTree.root.ST - 2 * child.ST)
            child.SSD = node.SSD + (self.total_leaves - 4 * child.nleaf) * (child.edge_length ** 2) + 2 * (node.SD - 2 * child.SDI) * child.edge_length
            SST, deltaT, deltaD, SDT, SSD = self.Update_var(child, node, child.edge_length)
            opt_function(child, SST, deltaT, deltaD, SDT, SSD, solver=self.solver)

    def prepare_root(self):
        root = self.get_root()
        root.SD = root.SDI
        #self.compute_dRoot_VAR() ########
        self.total_leaves = root.nleaf
        self.ddpTree.root.droot = 0
        self.ddpTree.root.troot = 0
        root.SD, root.SSD, root.SDT, self.SST = 0, 0, 0, 0
        for v in self.ddpTree.traverse_preorder():
            if not v.is_root():
                # must have defined edge lengths
                v.droot = v.parent.droot + v.edge_length
                if v.is_leaf():
                    root.SSD += (v.droot ** 2)
                    self.SST += (self.smplTimes[v.label] ** 2)
                    root.SD += v.droot
                    root.SDT += (v.droot * self.smplTimes[v.label])
        #print("SD:",root.SD,"  SSD:",root.SSD,"  SDT:", root.SDT, "  SST:", self.SST, "  ST:", root.ST)
        # function works for sample1 and sample2

    def opt_score(self):
        return self.RTT

    def report_score(self):
        return "RTT score: " + str(self.opt_score()/self.total_leaves)